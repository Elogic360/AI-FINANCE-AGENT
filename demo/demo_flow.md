# FinPilot AI — Live Demo Flow Script

## Pre-Demo Setup
```bash
# Terminal 1: Backend
cd /home/elogic360/Documents/CODELAB/AI_FINANCE_AGENT
PYTHONPATH=backend python3.12 -m uvicorn app.main:app --port 8099

# Terminal 2: Frontend
cd frontend && npx vite --port 5173
```

## Demo Script (5-7 minutes)

### 1. Register (30s)
- Open http://localhost:5173
- Click "Register"
- Business Name: "Mtaa Fashion Store"
- Email: "demo@finpilot.ai"
- Password: "demo123456"
- Click "Create account"

**Say:** "I'm setting up a clothing shop in Dar es Salaam. Let me create my account."

### 2. Dashboard Overview (30s)
- Point to Financial Health gauge
- Point to Revenue/Expenses cards
- Point to Alerts section
- Point to Quick Stats

**Say:** "This is my financial command center. I can see my health score, revenue, expenses, and alerts at a glance."

### 3. Upload Transactions (1 min)
- Go to Transactions page
- Click "Import CSV"
- Upload `demo/sample_transactions.csv`
- Show the imported transactions
- Point to category badges and status

**Say:** "I'm uploading my bank transactions. The system auto-categorizes them."

### 4. Upload Documents (1 min)
- Go to Documents page
- Drag and drop files or click upload
- Show the upload progress
- Show parse status

**Say:** "I can upload bank statements, invoices, receipts — PDF, Excel, CSV, images. The AI parses them automatically."

### 5. View Reports (1 min)
- Go to Reports page
- Click "Profit & Loss" tab
- Point to Revenue vs Expenses
- Click "Balance Sheet" tab
- Click "Trial Balance" tab
- Show balanced totals

**Say:** "All my financial reports are generated from the double-entry ledger. Every number is traceable."

### 6. Journal Entries (30s)
- Go to Journal page
- Show draft entries
- Click "Approve" on a draft
- Show status change to "Posted"

**Say:** "The AI proposes journal entries. I review and approve them. Nothing posts without my confirmation."

### 7. Ask AI CFO (1 min)
- Go to Dashboard
- Click "Ask AI CFO" or use the chat

**Type:** "Why is my cash position getting worse even though I'm profitable?"

**Expected response:** Structured FACT/ANALYSIS/RISK/RECOMMENDATION format

**Say:** "The AI CFO gives me grounded answers — not guesses. Every number comes from my actual ledger."

### 8. Business Startup Advice (1 min)

**Type:** "I want to open a clothing shop in Dar es Salaam with TZS 5 million capital. Give me a startup plan."

**Expected response:** Capital allocation, monthly costs, break-even analysis

**Say:** "FinPilot doesn't just track my current business — it helps me plan new ventures too."

### 9. Closing (30s)

**Say:** "FinPilot AI turns messy financial documents into clear, actionable intelligence. Every answer is grounded in your actual data — never AI guesswork. That's grounded transparency."

---

## Sample Prompts for Users

### Business Analysis
- "Analyse my company finance and tell me everything I need to know."
- "Why is my profit falling even though sales are up?"
- "Where am I spending too much?"

### Cash Flow
- "Kwa nini nina profit lakini cash yangu ni ndogo?"
- "What happens if sales decrease by 15%?"
- "How long can I survive at current burn rate?"

### Pricing
- "If I buy jeans for TZS 35,000, what price gives me 40% margin?"
- "Should I increase prices? What's the impact?"

### Startup Planning
- "Nataka kufungua duka la nguo Dar es Salaam. Nina TZS 5M."
- "What are the startup costs for a clothing shop?"
- "Can I afford to hire an employee at TZS 300,000/month?"

### Document Analysis
- "Analyse all my uploaded financial documents."
- "Compare my bank statement with my sales spreadsheet."
- "Find any unusual or suspicious transactions."

### Health Check
- "Give my business a financial health score."
- "What are my biggest financial risks?"

---

## Tanzania-Specific Data

### Sample Customers
- Anna Mwangi - Regular bulk buyer
- Benson Ochieng - M-Pesa customer
- Catherine Njeri - Dress specialist
- David Kimani - Wholesale account
- Esther Mushi - Walk-in customer
- Francis Otieno - Online orders
- Grace Mkwawa - VIP wholesale
- Hassan Juma - Cash buyer
- Irene Balira - Bulk orders
- Joseph Mkumbwa - Staff member

### Sample Vendors
- Kariakoo Wholesalers - Main stock supplier
- Tandahimba Supply Co - Fabrics
- Mwananyamala Distributors - Accessories
- Mikocheni Hardware - Shop maintenance
- Packaging Supplies Ltd - Packaging
- Clean Pro Tanzania - Cleaning

### Local Context
- Currency: TZS (Tanzanian Shilling)
- Payments: M-Pesa, TigoPesa, Airtel Money, CRDB Bank
- Suppliers: Kariakoo market, Tandahimba
- Services: TANESCO (electricity), Vodacom/Halotel (telecom)
- Location: Dar es Salaam, Tanzania
