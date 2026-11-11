import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Lock, Mail, AlertCircle, Clock } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { setAuthSession } from '@/lib/auth-store';
import type { TokenResponse } from '@votoseguro/api-client';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLocked, setIsLocked] = useState(false);

  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setIsLocked(false);

    try {
      const response = await api.post<TokenResponse>('/auth/login', {
        email: email.trim(),
        password,
      });

      setAuthSession(response.access_token, response.user, response.organization);

      if (response.user.role === 'PLATFORM_ADMIN') {
        navigate('/platform/console');
      } else {
        navigate('/workspace');
      }
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 423) {
        setIsLocked(true);
      }
      setError(err.message || 'Error al autenticar.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ballot-ivory-100 flex flex-col justify-center items-center p-4 font-sans">
      <div className="max-w-md w-full bg-white rounded-2xl border border-stone-300 shadow-electoral overflow-hidden">
        {/* Cabecera institucional */}
        <div className="bg-civic-navy-900 text-white p-8 text-center border-b border-civic-navy-800">
          <div className="w-12 h-12 rounded-xl bg-seal-emerald/20 border border-seal-emerald/40 flex items-center justify-center text-seal-emerald font-bold mx-auto mb-3">
            <Shield className="w-6 h-6" />
          </div>
          <h2 className="font-title text-2xl font-bold tracking-wide">VotoSeguro</h2>
          <p className="text-xs text-stone-300 font-mono mt-1">
            Portal Institucional de Autoridad Electoral
          </p>
        </div>

        {/* Formulario */}
        <div className="p-8 space-y-6">
          {error && (
            <div
              className={`p-4 rounded-xl border text-xs flex items-start space-x-2.5 ${
                isLocked
                  ? 'bg-seal-crimson-light border-seal-crimson text-seal-crimson-dark'
                  : 'bg-amber-50 border-amber-300 text-amber-900'
              }`}
            >
              {isLocked ? (
                <Clock className="w-4 h-4 shrink-0 mt-0.5 text-seal-crimson" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
              )}
              <div className="leading-relaxed font-medium">
                {error}
                {isLocked && (
                  <p className="text-[11px] mt-1 text-stone-600 font-sans">
                    Protección automática contra ataques de fuerza bruta activada (RF-03).
                  </p>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                Correo Electrónico
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@institucion.edu"
                  className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-civic-navy-900 hover:bg-civic-navy-800 text-white font-semibold text-xs rounded-lg shadow-sm transition-colors disabled:opacity-50 mt-2"
            >
              {isLoading ? 'Comprobando credenciales...' : 'Iniciar Sesión'}
            </button>
          </form>

          <div className="pt-4 border-t border-stone-200 text-center">
            <Link
              to="/request-election"
              className="text-xs text-stone-500 hover:text-civic-navy-900 font-semibold"
            >
              ¿Representa a una institución? Solicite su elección aquí
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
