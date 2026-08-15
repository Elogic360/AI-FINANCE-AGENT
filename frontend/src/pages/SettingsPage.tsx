import { useAuth } from '../hooks/useAuth';
import { Building2, Mail, Shield } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800 space-y-4">
        <h2 className="text-white font-semibold flex items-center gap-2"><Building2 size={18} /> Business Profile</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-gray-400 text-sm mb-1">Email</label>
            <div className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm">
              <Mail size={16} className="text-gray-500" /> {user?.email}
            </div>
          </div>
          <div>
            <label className="block text-gray-400 text-sm mb-1">Role</label>
            <div className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm">
              <Shield size={16} className="text-gray-500" /> {user?.role}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
        <h2 className="text-white font-semibold mb-4">Currency Settings</h2>
        <p className="text-gray-400 text-sm">Default: TZS (Tanzanian Shilling). Multi-currency support available for EUR and USD.</p>
      </div>

      <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
        <h2 className="text-white font-semibold mb-4">AI Providers</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-gray-400">Primary (Pawa AI)</span><span className="text-green-400">Configured</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Fallback (Gemini)</span><span className="text-green-400">Configured</span></div>
        </div>
      </div>
    </div>
  );
}
