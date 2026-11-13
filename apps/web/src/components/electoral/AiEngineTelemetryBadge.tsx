import React from 'react';
import { Sparkles, Cpu, ShieldCheck } from 'lucide-react';

interface AiEngineTelemetryBadgeProps {
  source?: string | null;
  modelName?: string | null;
  latencyMs?: number | null;
  className?: string;
  compact?: boolean;
}

export const AiEngineTelemetryBadge: React.FC<AiEngineTelemetryBadgeProps> = ({
  source,
  modelName = 'votoseguro-lfm3',
  latencyMs,
  className = '',
  compact = false,
}) => {
  const isNeuralTunnel =
    source === 'LFM3-1.7B_NEURAL_TUNNEL' ||
    (typeof source === 'string' && source.includes('NEURAL_TUNNEL'));
  const isLfm3Local = source === 'LFM3-1.7B';
  const isFallback = source === 'DETERMINISTIC_FALLBACK' || !source;

  if (isNeuralTunnel) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-900 border border-purple-200 shadow-2xs ${className}`}
        title="Inferencia neuronal ejecutada en el nodo de escritorio especializado vía túnel estático ngrok"
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span className="font-sans">
          🧠 {compact ? 'Túnel Estático' : `Procesado por ${modelName || 'votoseguro-lfm3'} en PC Local vía Túnel Estático`}
          {latencyMs ? ` (${Math.round(latencyMs)} ms)` : ''}
        </span>
      </div>
    );
  }

  if (isLfm3Local) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-900 border border-emerald-200 ${className}`}
        title="Inferencia local en modelo neuronal"
      >
        <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
        <span className="font-sans">
          🤖 {compact ? 'LFM3 Local' : `Motor Neuronal Local (${modelName || 'votoseguro-lfm3'})`}
          {latencyMs ? ` (${Math.round(latencyMs)} ms)` : ''}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200 ${className}`}
      title="El nodo neuronal de escritorio no estaba disponible; se ejecutó el motor determinista de contingencia"
    >
      <Cpu className="w-3.5 h-3.5 text-amber-600" />
      <span className="font-sans">
        ⚙️ {compact ? 'Modo Degradado' : 'Modo Degradado Determinista'}
      </span>
    </div>
  );
};
