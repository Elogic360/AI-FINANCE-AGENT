import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { extractErrorMessage } from '../lib/api';
import { UserPlus } from 'lucide-react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(email, password, businessName);
      navigate('/dashboard');
    } catch (err) {
      setError(extractErrorMessage(err, 'Registration failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 bg-cyan-500 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-lg">F</span>
            </div>
            <span className="text-white text-2xl font-bold">FinPilot</span>
          </div>
          <p className="text-gray-400">Create your financial command center</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-[#1a1a2e] rounded-2xl p-8 border border-gray-800">
          <h2 className="text-white text-xl font-semibold mb-6">Create account</h2>
          {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg mb-4 text-sm">{error}</div>}
          <div className="mb-4">
            <label className="block text-gray-400 text-sm mb-2">Business Name</label>
            <input type="text" value={businessName} onChange={e => setBusinessName(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="Mlimani Mini Market" required />
          </div>
          <div className="mb-4">
            <label className="block text-gray-400 text-sm mb-2">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="you@business.com" required />
          </div>
          <div className="mb-6">
            <label className="block text-gray-400 text-sm mb-2">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="Min 8 characters" minLength={8} required />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-3 rounded-lg transition flex items-center justify-center gap-2 disabled:opacity-50">
            <UserPlus size={18} />
            {loading ? 'Creating...' : 'Create account'}
          </button>
          <p className="text-gray-400 text-sm text-center mt-4">
            Already have an account? <Link to="/login" className="text-cyan-400 hover:text-cyan-300">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
