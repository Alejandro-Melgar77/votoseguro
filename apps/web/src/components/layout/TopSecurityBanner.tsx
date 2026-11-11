import React, { useEffect, useState } from 'react';
import { Shield, Clock, Globe, UserCheck, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/lib/auth-store';
import { formatElectoralDateTime } from '@/lib/timezone';

interface TopSecurityBannerProps {
  timezone?: string;
}

export const TopSecurityBanner: React.FC<TopSecurityBannerProps> = ({
  timezone = 'America/La_Paz',
}) => {
  const { user, organization, isAdminSegment } = useAuth();
  const [currentServerTime, setCurrentServerTime] = useState<Date>(new Date());

  // Simulación y actualización constante del reloj sincronizado
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentServerTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-civic-navy-950 text-stone-200 border-b border-civic-navy-800 text-xs px-4 py-2 flex flex-wrap items-center justify-between gap-3 shadow-sm select-none">
      {/* Sección Izquierda: Institución y Estado */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 text-stone-300 font-medium">
          <Shield className="w-4 h-4 text-seal-emerald" />
          <span className="font-semibold tracking-wide">
            {organization?.name || 'VotoSeguro — Corte Electoral Central'}
          </span>
        </div>

        {isAdminSegment ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3 mr-1" />
            MODO DELEGADO: SOLO LECTURA
          </span>
        ) : (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-civic-navy-800 text-stone-300 border border-civic-navy-700">
            <UserCheck className="w-3 h-3 mr-1 text-seal-emerald" />
            {user?.role || 'INVITADO'}
          </span>
        )}
      </div>

      {/* Sección Derecha: Reloj Oficial y Zona Horaria */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-1 text-stone-400">
          <Globe className="w-3.5 h-3.5 text-stone-400" />
          <span className="font-mono text-[11px]">{timezone}</span>
        </div>

        <div className="flex items-center space-x-1.5 bg-civic-navy-900/80 px-2.5 py-1 rounded border border-civic-navy-800">
          <Clock className="w-3.5 h-3.5 text-seal-emerald" />
          <span className="text-stone-400 font-medium">Hora Oficial Servidor:</span>
          <span className="font-mono font-bold text-white tracking-wider">
            {formatElectoralDateTime(currentServerTime, timezone)}
          </span>
        </div>
      </div>
    </div>
  );
};
