import React, { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { calculateRemainingSeconds } from '@/lib/timezone';

interface PhaseCountdownClockProps {
  targetDate: string | Date;
  label: string;
  onExpire?: () => void;
}

export const PhaseCountdownClock: React.FC<PhaseCountdownClockProps> = ({
  targetDate,
  label,
  onExpire,
}) => {
  const [remainingSeconds, setRemainingSeconds] = useState<number>(() =>
    calculateRemainingSeconds(targetDate)
  );

  useEffect(() => {
    const updateCountdown = () => {
      const remaining = calculateRemainingSeconds(targetDate);
      setRemainingSeconds(remaining);
      if (remaining <= 0 && onExpire) {
        onExpire();
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [targetDate, onExpire]);

  const days = Math.floor(remainingSeconds / 86400);
  const hours = Math.floor((remainingSeconds % 86400) / 3600);
  const minutes = Math.floor((remainingSeconds % 3600) / 60);
  const seconds = remainingSeconds % 60;

  const pad = (n: number) => n.toString().padStart(2, '0');

  return (
    <div className="bg-civic-navy-950 text-white rounded-xl p-5 border border-civic-navy-800 shadow-electoral flex flex-col sm:flex-row items-center justify-between gap-4">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-lg bg-seal-emerald/10 border border-seal-emerald/30 flex items-center justify-center text-seal-emerald">
          <Clock className="w-5 h-5" />
        </div>
        <div>
          <span className="text-[11px] font-mono tracking-wider text-stone-400 uppercase">
            Reloj de Precisión Electoral
          </span>
          <h4 className="text-sm font-semibold text-stone-200">{label}</h4>
        </div>
      </div>

      {remainingSeconds > 0 ? (
        <div className="flex items-center space-x-2 font-mono">
          <div className="bg-civic-navy-900 border border-civic-navy-800 rounded px-3 py-1.5 text-center min-w-[50px]">
            <span className="block text-lg font-bold text-white tracking-wider">
              {pad(days)}
            </span>
            <span className="text-[9px] uppercase text-stone-400">Días</span>
          </div>
          <span className="text-stone-500 font-bold">:</span>
          <div className="bg-civic-navy-900 border border-civic-navy-800 rounded px-3 py-1.5 text-center min-w-[50px]">
            <span className="block text-lg font-bold text-white tracking-wider">
              {pad(hours)}
            </span>
            <span className="text-[9px] uppercase text-stone-400">Horas</span>
          </div>
          <span className="text-stone-500 font-bold">:</span>
          <div className="bg-civic-navy-900 border border-civic-navy-800 rounded px-3 py-1.5 text-center min-w-[50px]">
            <span className="block text-lg font-bold text-white tracking-wider">
              {pad(minutes)}
            </span>
            <span className="text-[9px] uppercase text-stone-400">Min</span>
          </div>
          <span className="text-stone-500 font-bold">:</span>
          <div className="bg-civic-navy-900 border border-civic-navy-800 rounded px-3 py-1.5 text-center min-w-[50px]">
            <span className="block text-lg font-bold text-seal-amber tracking-wider">
              {pad(seconds)}
            </span>
            <span className="text-[9px] uppercase text-stone-400">Seg</span>
          </div>
        </div>
      ) : (
        <div className="px-4 py-2 rounded bg-seal-crimson/20 border border-seal-crimson/40 text-seal-crimson font-mono text-xs font-bold uppercase tracking-wider">
          Plazo Finalizado
        </div>
      )}
    </div>
  );
};
