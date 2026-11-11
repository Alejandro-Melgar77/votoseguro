import React from 'react';
import { History, ArrowRight, ShieldCheck, User } from 'lucide-react';
import type { ScheduleChange } from '@votoseguro/api-client';
import { formatElectoralDateTime } from '@/lib/timezone';

interface ScheduleAuditTimelineProps {
  changes: ScheduleChange[];
  timezone?: string;
}

export const ScheduleAuditTimeline: React.FC<ScheduleAuditTimelineProps> = ({
  changes,
  timezone = 'America/La_Paz',
}) => {
  if (!changes || changes.length === 0) {
    return (
      <div className="bg-white border border-stone-300 rounded-xl p-8 text-center shadow-sm">
        <History className="w-8 h-8 text-stone-300 mx-auto mb-2" />
        <h4 className="text-xs font-semibold text-stone-600">
          Sin modificaciones de cronograma registradas
        </h4>
        <p className="text-[11px] text-stone-400 mt-1">
          El cronograma original de la elección se mantiene intacto sin enmiendas posteriores.
        </p>
      </div>
    );
  }

  const formatFieldName = (name: string) => {
    switch (name) {
      case 'registration_opens_at':
        return 'Inicio de Registro';
      case 'registration_closes_at':
        return 'Fin de Registro';
      case 'voting_opens_at':
        return 'Inicio de Votación';
      case 'voting_closes_at':
        return 'Fin de Votación';
      default:
        return name;
    }
  };

  return (
    <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-electoral space-y-4">
      <div className="flex items-center space-x-2 border-b border-stone-200 pb-3">
        <History className="w-4 h-4 text-seal-amber" />
        <h3 className="font-title text-sm font-bold text-civic-navy-900">
          Historial Inmutable de Cambios de Cronograma (schedule_change)
        </h3>
      </div>

      <div className="space-y-4">
        {changes.map((item) => (
          <div
            key={item.id}
            className="border-l-2 border-seal-amber pl-4 py-1 space-y-1.5 relative"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs font-bold text-civic-navy-900 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
                {formatFieldName(item.field_name)}
              </span>
              <span className="text-[11px] font-mono text-stone-500">
                {formatElectoralDateTime(item.changed_at, timezone)}
              </span>
            </div>

            {/* Comparación Git-Diff */}
            <div className="flex items-center space-x-2 text-xs font-mono bg-stone-50 p-2.5 rounded border border-stone-200">
              <span className="text-seal-crimson line-through">
                {formatElectoralDateTime(item.old_value, timezone)}
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-stone-400 shrink-0" />
              <span className="text-seal-emerald font-bold">
                {formatElectoralDateTime(item.new_value, timezone)}
              </span>
            </div>

            {/* Motivo Oficial y Metadatos */}
            <div className="text-xs text-stone-700 bg-amber-50/50 p-2 rounded border border-amber-200/60">
              <span className="font-semibold text-amber-900">Motivo: </span>
              <span>{item.reason}</span>
            </div>

            <div className="flex items-center space-x-2 text-[10px] text-stone-400 font-mono">
              <span>Estado en ese momento: </span>
              <span className="font-semibold text-stone-600">{item.election_status_at_change}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
