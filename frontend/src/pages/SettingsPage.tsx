import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Building2, Mail, Shield, Bell, Bot, Key, Save, Check, User, CreditCard } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<'profile' | 'organization' | 'ai' | 'notifications'>('profile');

  // Form states
  const [orgName, setOrgName] = useState('');
  const [orgCountry, setOrgCountry] = useState('Tanzania');
  const [orgCurrency, setOrgCurrency] = useState('TZS');
  const [orgFiscalYear, setOrgFiscalYear] = useState('January');
  const [aiPrimary, setAiPrimary] = useState('pawa-ai');
  const [aiFallback, setAiFallback] = useState('gemini');
  const [aiAutoCategory, setAiAutoCategory] = useState(true);
  const [aiAutoJournal, setAiAutoJournal] = useState(true);
  const [notifyEmail, setNotifyEmail] = useState(true);
  const [notifyOverdue, setNotifyOverdue] = useState(true);
  const [notifyAlerts, setNotifyAlerts] = useState(true);
  const [notifyWeekly, setNotifyWeekly] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const tabs = [
    { key: 'profile' as const, label: 'Profile', icon: User },
    { key: 'organization' as const, label: 'Organization', icon: Building2 },
    { key: 'ai' as const, label: 'AI Providers', icon: Bot },
    { key: 'notifications' as const, label: 'Notifications', icon: Bell },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-gray-400 text-sm mt-1">Manage your account and preferences</p>
        </div>
        <button
          onClick={handleSave}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
            saved ? 'bg-green-500/10 text-green-400 border border-green-500/30' : 'bg-cyan-500 hover:bg-cyan-600 text-white'
          }`}
        >
          {saved ? <><Check size={16} /> Saved</> : <><Save size={16} /> Save Changes</>}
        </button>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Tab Navigation */}
        <div className="lg:w-56 flex lg:flex-col gap-2 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm whitespace-nowrap transition ${
                activeTab === tab.key
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-gray-400 hover:bg-gray-800/50 hover:text-white border border-transparent'
              }`}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 space-y-6">
          {/* Profile */}
          {activeTab === 'profile' && (
            <>
              <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
                <h2 className="text-white font-semibold flex items-center gap-2 mb-6"><User size={18} /> User Profile</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Email Address</label>
                    <div className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm">
                      <Mail size={16} className="text-gray-500" /> {user?.email}
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Role</label>
                    <div className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm">
                      <Shield size={16} className="text-gray-500" /> {user?.role}
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">User ID</label>
                    <div className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-400 text-sm font-mono">
                      {user?.id?.slice(0, 8)}...
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Member Since</label>
                    <div className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm">
                      {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
                <h2 className="text-white font-semibold flex items-center gap-2 mb-4"><Key size={18} /> Security</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Current Password</label>
                    <input type="password" placeholder="Enter current password"
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-gray-400 text-sm mb-1.5">New Password</label>
                      <input type="password" placeholder="New password"
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
                    </div>
                    <div>
                      <label className="block text-gray-400 text-sm mb-1.5">Confirm Password</label>
                      <input type="password" placeholder="Confirm new password"
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
                    Update Password
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Organization */}
          {activeTab === 'organization' && (
            <>
              <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
                <h2 className="text-white font-semibold flex items-center gap-2 mb-6"><Building2 size={18} /> Organization Settings</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Business Name</label>
                    <input type="text" value={orgName} onChange={e => setOrgName(e.target.value)} placeholder="Your Business Name"
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Country</label>
                    <select value={orgCountry} onChange={e => setOrgCountry(e.target.value)}
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                      <option>Tanzania</option>
                      <option>Kenya</option>
                      <option>Uganda</option>
                      <option>Rwanda</option>
                      <option>Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Default Currency</label>
                    <select value={orgCurrency} onChange={e => setOrgCurrency(e.target.value)}
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                      <option value="TZS">TZS - Tanzanian Shilling</option>
                      <option value="KES">KES - Kenyan Shilling</option>
                      <option value="USD">USD - US Dollar</option>
                      <option value="EUR">EUR - Euro</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Fiscal Year Start</label>
                    <select value={orgFiscalYear} onChange={e => setOrgFiscalYear(e.target.value)}
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                      {['January','February','March','April','May','June','July','August','September','October','November','December'].map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
                <h2 className="text-white font-semibold flex items-center gap-2 mb-4"><CreditCard size={18} /> Billing</h2>
                <div className="bg-gray-800/30 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white font-medium">Free Plan</p>
                      <p className="text-gray-400 text-sm">Basic features for small businesses</p>
                    </div>
                    <button className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm transition">
                      Upgrade
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* AI Providers */}
          {activeTab === 'ai' && (
            <>
              <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
                <h2 className="text-white font-semibold flex items-center gap-2 mb-6"><Bot size={18} /> AI Provider Configuration</h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-gray-400 text-sm mb-1.5">Primary AI Provider</label>
                      <select value={aiPrimary} onChange={e => setAiPrimary(e.target.value)}
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                        <option value="pawa-ai">Pawa AI</option>
                        <option value="gemini">Google Gemini</option>
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-400 text-sm mb-1.5">Fallback Provider</label>
                      <select value={aiFallback} onChange={e => setAiFallback(e.target.value)}
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                        <option value="gemini">Google Gemini</option>
                        <option value="pawa-ai">Pawa AI</option>
                        <option value="openai">OpenAI</option>
                        <option value="none">None</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex items-center justify-between py-3 border-b border-gray-800/50">
                    <div>
                      <p className="text-white text-sm font-medium">Auto-categorize Transactions</p>
                      <p className="text-gray-500 text-xs">AI automatically assigns categories to new transactions</p>
                    </div>
                    <button onClick={() => setAiAutoCategory(!aiAutoCategory)}
                      className={`relative w-11 h-6 rounded-full transition ${aiAutoCategory ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                      <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${aiAutoCategory ? 'translate-x-5' : ''}`} />
                    </button>
                  </div>
                  <div className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-white text-sm font-medium">Auto-generate Journal Entries</p>
                      <p className="text-gray-500 text-xs">AI creates draft journal entries from transactions</p>
                    </div>
                    <button onClick={() => setAiAutoJournal(!aiAutoJournal)}
                      className={`relative w-11 h-6 rounded-full transition ${aiAutoJournal ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                      <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${aiAutoJournal ? 'translate-x-5' : ''}`} />
                    </button>
                  </div>
                </div>
              </div>

              <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
                <h2 className="text-white font-semibold flex items-center gap-2 mb-4"><Key size={18} /> API Keys</h2>
                <div className="space-y-3">
                  {[
                    { name: 'Pawa AI', configured: true },
                    { name: 'Google Gemini', configured: true },
                    { name: 'OpenAI', configured: false },
                  ].map(provider => (
                    <div key={provider.name} className="flex items-center justify-between py-2 border-b border-gray-800/50 last:border-0">
                      <span className="text-gray-300 text-sm">{provider.name}</span>
                      <span className={`text-xs px-2 py-1 rounded ${provider.configured ? 'bg-green-500/10 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                        {provider.configured ? 'Configured' : 'Not set'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Notifications */}
          {activeTab === 'notifications' && (
            <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
              <h2 className="text-white font-semibold flex items-center gap-2 mb-6"><Bell size={18} /> Notification Preferences</h2>
              <div className="space-y-1">
                {[
                  { label: 'Email Notifications', desc: 'Receive notifications via email', state: notifyEmail, setter: setNotifyEmail },
                  { label: 'Overdue Invoice Alerts', desc: 'Get notified when invoices become overdue', state: notifyOverdue, setter: setNotifyOverdue },
                  { label: 'System Alerts', desc: 'Receive alerts for anomalies and issues', state: notifyAlerts, setter: setNotifyAlerts },
                  { label: 'Weekly Summary', desc: 'Get a weekly financial summary email', state: notifyWeekly, setter: setNotifyWeekly },
                ].map(item => (
                  <div key={item.label} className="flex items-center justify-between py-3 border-b border-gray-800/50 last:border-0">
                    <div>
                      <p className="text-white text-sm font-medium">{item.label}</p>
                      <p className="text-gray-500 text-xs">{item.desc}</p>
                    </div>
                    <button onClick={() => item.setter(!item.state)}
                      className={`relative w-11 h-6 rounded-full transition ${item.state ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                      <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${item.state ? 'translate-x-5' : ''}`} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
