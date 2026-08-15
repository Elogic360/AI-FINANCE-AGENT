"""
FinPilot AI Orchestrator — routes requests to the appropriate agent and provider.

The orchestrator:
1. Receives a user message
2. Selects the best agent based on keyword matching and context
3. Selects the best provider based on agent preference and capabilities
4. Executes the agent's system prompt + user message with tools
5. Handles tool execution (calling mock tools and feeding results back)
6. Returns the final response

All implementations are MOCK for development.
"""

import json
import logging
import uuid
from typing import Any, AsyncIterator
from datetime import datetime

from app.ai.base import AIProvider, AIResponse, StreamChunk, TaskType
from app.ai.agents import (
    AgentDefinition,
    AGENT_REGISTRY,
    ALL_AGENTS,
    CFO_AGENT,
)
from app.ai.tools import TOOL_REGISTRY, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


# ── Agent selection ────────────────────────────────────────────────────────

def select_agent(message: str, context: dict[str, Any] | None = None) -> AgentDefinition:
    """
    Select the best agent for a given user message.

    Uses keyword matching with scoring. The agent with the highest
    keyword match score wins. Ties go to the CFO agent (generalist).
    """
    message_lower = message.lower()
    scores: dict[str, int] = {}

    for agent in ALL_AGENTS:
        score = 0
        for keyword in agent.routing_keywords:
            if keyword.lower() in message_lower:
                # Longer keywords get higher weight
                score += len(keyword.split())
        scores[agent.id] = score

    # Find the agent with the highest score
    best_agent_id = max(scores, key=scores.get)
    best_score = scores[best_agent_id]

    # If no keywords matched or tie, default to CFO
    if best_score == 0:
        logger.debug(f"No keyword match for '{message[:50]}...', defaulting to CFO")
        return CFO_AGENT

    selected = AGENT_REGISTRY[best_agent_id]
    logger.debug(f"Selected agent: {selected.name} (score={best_score})")
    return selected


# ── Provider selection ─────────────────────────────────────────────────────

def select_provider(
    agent: AgentDefinition,
    providers: dict[str, AIProvider],
) -> AIProvider | None:
    """
    Select the best provider for an agent's request.

    Respects agent's preferred_provider if available.
    Falls back to any provider with chat capability.
    """
    # Try preferred provider first
    if agent.preferred_provider and agent.preferred_provider in providers:
        provider = providers[agent.preferred_provider]
        logger.debug(f"Using preferred provider: {provider.name}")
        return provider

    # Fall back to any available provider
    for name, provider in providers.items():
        if provider.supports(TaskType.CHAT):
            logger.debug(f"Falling back to provider: {provider.name}")
            return provider

    return None


# ── Tool execution ─────────────────────────────────────────────────────────

async def execute_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    org_id: str,
) -> dict[str, Any]:
    """
    Execute a tool call from the AI model.

    Looks up the tool in TOOL_REGISTRY and calls it with the provided arguments.
    Always injects org_id if the tool expects it and it wasn't provided.
    """
    func = TOOL_REGISTRY.get(tool_name)
    if not func:
        return {"error": f"Unknown tool: {tool_name}"}

    # Inject org_id if the tool expects it
    if "org_id" not in arguments:
        arguments["org_id"] = org_id

    try:
        result = await func(**arguments)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_name} — {e}")
        return {"error": str(e)}


# ── Orchestrator ───────────────────────────────────────────────────────────

class AIOrchestrator:
    """
    Main orchestrator for FinPilot AI.

    Manages providers, routes requests to agents, handles tool calling loops,
    and returns final responses to the API layer.

    Usage:
        orchestrator = AIOrchestrator()
        orchestrator.register_provider(PawaProvider())
        orchestrator.register_provider(GeminiProvider())

        response = await orchestrator.chat(
            message="What is my revenue this month?",
            org_id="org_001",
            conversation_history=[],
        )
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._conversation_store: dict[str, list[dict]] = {}

    def register_provider(self, provider: AIProvider) -> None:
        """Register an AI provider."""
        self._providers[provider.name] = provider
        logger.info(f"Registered AI provider: {provider.name}")

    @property
    def providers(self) -> dict[str, AIProvider]:
        return self._providers

    async def chat(
        self,
        message: str,
        org_id: str,
        conversation_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        agent_id: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """
        Process a chat message through the orchestrator.

        Steps:
        1. Select agent (by ID or keyword matching)
        2. Select provider (by agent preference)
        3. Build messages array with system prompt + history + user message
        4. Call provider with tools
        5. If tool calls returned, execute them and loop
        6. Return final response

        Returns a dict with:
        - response: str (the AI's text response)
        - agent: str (which agent handled it)
        - provider: str (which provider was used)
        - tool_calls: list (any tools that were called)
        - conversation_id: str (for continuing the conversation)
        - metadata: dict
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"

        # Select agent
        if agent_id and agent_id in AGENT_REGISTRY:
            agent = AGENT_REGISTRY[agent_id]
        else:
            agent = select_agent(message)

        # Select provider
        provider = select_provider(agent, self._providers)
        if not provider:
            return {
                "response": "I'm sorry, no AI providers are currently available. Please try again later.",
                "agent": agent.name,
                "provider": None,
                "tool_calls": [],
                "conversation_id": conversation_id,
                "error": "no_provider_available",
            }

        # Build messages
        messages = self._build_messages(
            agent=agent,
            message=message,
            org_id=org_id,
            conversation_history=conversation_history or [],
        )

        # Get tools for this agent
        agent_tools = [
            t for t in TOOL_DEFINITIONS
            if t["function"]["name"] in agent.tools
        ]

        # Call provider (with tool calling loop, max 3 iterations)
        tool_calls_made: list[dict] = []
        final_response = ""

        for iteration in range(3):
            response = await provider.chat(
                messages=messages,
                tools=agent_tools if agent_tools else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
            )

            # Check for tool calls
            tool_calls = response.metadata.get("tool_calls", [])
            if not tool_calls:
                final_response = response.result
                break

            # Execute tool calls
            logger.info(f"Executing {len(tool_calls)} tool calls (iteration {iteration + 1})")
            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                try:
                    args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                tool_result = await execute_tool_call(func_name, args, org_id)
                tool_calls_made.append({
                    "tool": func_name,
                    "arguments": args,
                    "result_summary": str(tool_result)[:200],
                })

                # Add tool result to messages for the next iteration
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": json.dumps(tool_result, default=str),
                })

        # Store conversation
        self._conversation_store.setdefault(conversation_id, []).extend([
            {"role": "user", "content": message, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": final_response, "timestamp": datetime.utcnow().isoformat()},
        ])

        return {
            "response": final_response,
            "agent": agent.name,
            "agent_id": agent.id,
            "provider": provider.name,
            "tool_calls": tool_calls_made,
            "conversation_id": conversation_id,
            "metadata": {
                "model": provider.name,
                "temperature": agent.temperature,
                "tools_available": len(agent_tools),
                "tools_called": len(tool_calls_made),
            },
        }

    async def stream_chat(
        self,
        message: str,
        org_id: str,
        conversation_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        agent_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Streaming version of chat.

        Yields dicts with:
        - type: "chunk" | "tool_call" | "done" | "error"
        - content: str (for chunks)
        - metadata: dict
        """
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"

        if agent_id and agent_id in AGENT_REGISTRY:
            agent = AGENT_REGISTRY[agent_id]
        else:
            agent = select_agent(message)

        provider = select_provider(agent, self._providers)
        if not provider:
            yield {
                "type": "error",
                "content": "No AI providers available",
                "conversation_id": conversation_id,
            }
            return

        messages = self._build_messages(
            agent=agent,
            message=message,
            org_id=org_id,
            conversation_history=conversation_history or [],
        )

        agent_tools = [
            t for t in TOOL_DEFINITIONS
            if t["function"]["name"] in agent.tools
        ]

        # Stream the response
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=messages,
            tools=agent_tools if agent_tools else None,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
        ):
            if chunk.content:
                full_response += chunk.content
                yield {
                    "type": "chunk",
                    "content": chunk.content,
                    "agent": agent.name,
                    "provider": provider.name,
                    "conversation_id": conversation_id,
                }

            if chunk.finish_reason == "stop":
                yield {
                    "type": "done",
                    "content": full_response,
                    "agent": agent.name,
                    "agent_id": agent.id,
                    "provider": provider.name,
                    "conversation_id": conversation_id,
                }

    async def parse_document(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str,
        org_id: str,
    ) -> dict[str, Any]:
        """Parse a document using the best available provider."""
        provider = self._providers.get("pawa") or list(self._providers.values())[0]
        result = await provider.parse_document(file_content, mime_type, filename)
        return {
            "content": result.content,
            "mime_type": result.mime_type,
            "pages": result.pages,
            "tables": result.tables,
            "metadata": result.metadata,
            "confidence": result.confidence,
            "provider": provider.name,
        }

    async def embed_text(
        self,
        text: str | list[str],
    ) -> list[list[float]]:
        """Generate embeddings using the best available provider."""
        provider = self._providers.get("pawa") or list(self._providers.values())[0]
        return await provider.embed(text)

    def get_conversation(self, conversation_id: str) -> list[dict]:
        """Retrieve conversation history."""
        return self._conversation_store.get(conversation_id, [])

    async def health_check(self) -> dict[str, bool]:
        """Check health of all registered providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    def _build_messages(
        self,
        agent: AgentDefinition,
        message: str,
        org_id: str,
        conversation_history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the messages array for the AI provider."""
        system_prompt = agent.system_prompt + f"\n\nCurrent organization ID: {org_id}"
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 20 messages to stay within context)
        for msg in conversation_history[-20:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current user message
        messages.append({"role": "user", "content": message})

        return messages


# Global singleton orchestrator
orchestrator = AIOrchestrator()
