import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Vote,
  CalendarDays,
  Users,
  ShieldCheck,
  Building2,
  LogOut,
  FileText,
} from 'lucide-react';
import { useAuth } from '@/lib/auth-store';
import { TopSecurityBanner } from './TopSecurityBanner';

interface InstitutionalShellProps {
  children: React.ReactNode;
  activeElectionId?: string;
  timezone?: string;
}

export const InstitutionalShell: React.FC<InstitutionalShellProps> = ({
  children,
  activeElectionId,
  timezone,
}) => {
  const { user, isPlatformAdmin, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-ballot-ivory-100 font-sans">
      {/* 1. Barra Superior de Seguridad y Reloj */}
      <TopSecurityBanner timezone={timezone} />

      <div className="flex-1 flex overflow-hidden">
        {/* 2. Barra Lateral Institucional */}
        <aside className="w-64 bg-civic-navy-900 text-stone-300 flex flex-col border-r border-civic-navy-800 shrink-0">
          <div className="p-5 border-b border-civic-navy-800">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded bg-seal-emerald/20 border border-seal-emerald/40 flex items-center justify-center text-seal-emerald font-bold">
                VS
              </div>
              <div>
                <h1 className="font-title text-base font-bold text-white tracking-wide">
                  VotoSeguro v1.0
                </h1>
                <p className="text-[11px] text-stone-400 font-sans">
                  Soberanía Cívica Auditada
                </p>
              </div>
            </div>
          </div>

          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {isPlatformAdmin ? (
              <>
                <div className="px-3 pt-3 pb-1 text-[10px] font-mono tracking-wider text-stone-400 uppercase">
                  Operador Central
                </div>
                <Link
                  to="/platform/console"
                  className={`flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    location.pathname === '/platform/console'
                      ? 'bg-civic-navy-800 text-white font-semibold'
                      : 'hover:bg-civic-navy-800/60 text-stone-300'
                  }`}
                >
                  <Building2 className="w-4 h-4 text-seal-emerald" />
                  <span>Consola de Plataforma</span>
                </Link>
              </>
            ) : (
              <>
                <div className="px-3 pt-3 pb-1 text-[10px] font-mono tracking-wider text-stone-400 uppercase">
                  Gestión Institucional
                </div>
                <Link
                  to="/workspace"
                  className={`flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    location.pathname === '/workspace'
                      ? 'bg-civic-navy-800 text-white font-semibold'
                      : 'hover:bg-civic-navy-800/60 text-stone-300'
                  }`}
                >
                  <Vote className="w-4 h-4 text-seal-emerald" />
                  <span>Elecciones</span>
                </Link>

                {activeElectionId && (
                  <>
                    <div className="px-3 pt-4 pb-1 text-[10px] font-mono tracking-wider text-stone-400 uppercase">
                      Control Electoral
                    </div>
                    <Link
                      to={`/elections/${activeElectionId}/schedule`}
                      className={`flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                        location.pathname.includes('/schedule')
                          ? 'bg-civic-navy-800 text-white font-semibold'
                          : 'hover:bg-civic-navy-800/60 text-stone-300'
                      }`}
                    >
                      <CalendarDays className="w-4 h-4 text-seal-amber" />
                      <span>Panel de Cronograma</span>
                    </Link>

                    <Link
                      to={`/elections/${activeElectionId}/delegates`}
                      className={`flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                        location.pathname.includes('/delegates')
                          ? 'bg-civic-navy-800 text-white font-semibold'
                          : 'hover:bg-civic-navy-800/60 text-stone-300'
                      }`}
                    >
                      <Users className="w-4 h-4 text-seal-emerald" />
                      <span>Administradores Delegados</span>
                    </Link>
                  </>
                )}
              </>
            )}

            <div className="pt-4 border-t border-civic-navy-800 mt-4">
              <Link
                to="/request-election"
                className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-medium text-stone-400 hover:text-white hover:bg-civic-navy-800/40 transition-colors"
              >
                <FileText className="w-4 h-4 text-stone-400" />
                <span>Formulario Público</span>
              </Link>
            </div>
          </nav>

          {/* Perfil inferior y logout */}
          <div className="p-3 border-t border-civic-navy-800 bg-civic-navy-950/60">
            <div className="flex items-center justify-between">
              <div className="min-w-0 pr-2">
                <p className="text-xs font-semibold text-white truncate">
                  {user?.full_name}
                </p>
                <p className="text-[11px] text-stone-400 truncate">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                title="Cerrar Sesión"
                className="p-1.5 rounded hover:bg-civic-navy-800 text-stone-400 hover:text-seal-crimson transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </aside>

        {/* 3. Área de Contenido Principal */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          <div className="max-w-6xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
