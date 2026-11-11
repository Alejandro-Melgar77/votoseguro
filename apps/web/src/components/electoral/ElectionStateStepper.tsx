import React from 'react';
import { Lock, CheckCircle2, PlayCircle, Clock } from 'lucide-react';
import type { ElectionStatus } from '@votoseguro/api-client';

interface ElectionStateStepperProps {
  currentStatus: ElectionStatus;
}

interface StepConfig {
  key: ElectionStatus;
  label: string;
  sublabel: string;
}

const PHASES: StepConfig[] = [
  { key: 'DRAFT', label: 'Borrador', sublabel: 'Configuración libre' },
  { key: 'SCHEDULED', label: 'Programada', sublabel: 'Estructura congelada' },
  { key: 'REGISTRATION_OPEN', label: 'Registro Abierto', sublabel: 'Padrón editable' },
  { key: 'REGISTRATION_CLOSED', label: 'Registro Cerrado', sublabel: 'Padrón congelado' },
  { key: 'VOTING_OPEN', label: 'Votación Abierta', sublabel: 'Emisión de votos' },
  { key: 'VOTING_CLOSED', label: 'Votación Cerrada', sublabel: 'Recepción bloqueada' },
  { key: 'TALLIED', label: 'Escrutada', sublabel: 'Resultados finales' },
];

export const ElectionStateStepper: React.FC<ElectionStateStepperProps> = ({ currentStatus }) => {
  if (currentStatus === 'CANCELLED') {
    return (
      <div className="bg-seal-crimson-light border border-seal-crimson text-seal-crimson-dark px-4 py-3 rounded-lg text-sm font-semibold flex items-center space-x-2">
        <Lock className="w-5 h-5 text-seal-crimson" />
        <span>PROCESO ELECTORAL CANCELADO — Todas las fases han sido anuladas.</span>
      </div>
    );
  }

  const currentIndex = PHASES.findIndex((p) => p.key === currentStatus);

  return (
    <div className="bg-white border border-stone-300 rounded-xl p-5 shadow-electoral">
      <div className="flex items-center justify-between relative">
        {/* Línea conectora de fondo */}
        <div className="absolute top-4 left-6 right-6 h-0.5 bg-stone-200 -z-0" />

        {PHASES.map((phase, idx) => {
          const isPast = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const isFuture = idx > currentIndex;

          return (
            <div
              key={phase.key}
              className="flex flex-col items-center relative z-10 text-center max-w-[110px]"
            >
              {/* Círculo indicador de estado */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  isCurrent
                    ? 'bg-seal-emerald text-white ring-4 ring-seal-emerald/20 shadow-md font-bold'
                    : isPast
                    ? 'bg-civic-navy-900 text-stone-200 border border-civic-navy-800'
                    : 'bg-stone-100 text-stone-400 border border-stone-300'
                }`}
              >
                {isPast ? (
                  <Lock className="w-3.5 h-3.5 text-stone-300" />
                ) : isCurrent ? (
                  <PlayCircle className="w-4 h-4 text-white animate-pulse" />
                ) : (
                  <Clock className="w-3.5 h-3.5 text-stone-400" />
                )}
              </div>

              {/* Textos de la fase */}
              <span
                className={`mt-2 text-xs font-semibold leading-tight ${
                  isCurrent
                    ? 'text-seal-emerald'
                    : isPast
                    ? 'text-civic-navy-900'
                    : 'text-stone-400'
                }`}
              >
                {phase.label}
              </span>
              <span className="text-[10px] text-stone-500 font-mono mt-0.5 leading-tight">
                {phase.sublabel}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
