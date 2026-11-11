import React, { useState } from 'react';
import { X, AlertCircle, Lock, CheckCircle2, ArrowRight } from 'lucide-react';
import type { Election, ScheduleUpdateRequest } from '@votoseguro/api-client';
import { formatDateTimeLocalInput, formatElectoralDateTime } from '@/lib/timezone';

interface ScheduleEditModalProps {
  election: Election;
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: ScheduleUpdateRequest) => Promise<void>;
  isLoading: boolean;
}

export const ScheduleEditModal: React.FC<ScheduleEditModalProps> = ({
  election,
  isOpen,
  onClose,
  onSave,
  isLoading,
}) => {
  if (!isOpen) return null;

  const status = election.status;

  // Determinar permisos de edición según reglas de la Sección 5.4
  const isDraft = status === 'DRAFT';
  const isScheduled = status === 'SCHEDULED';
  const isRegOpen = status === 'REGISTRATION_OPEN';
  const isRegClosed = status === 'REGISTRATION_CLOSED';
  const isVotingOpen = status === 'VOTING_OPEN';

  const canEditRegOpen = isDraft || isScheduled;
  const canEditRegClose = isDraft || isScheduled || isRegOpen;
  const canEditVoteOpen = isDraft || isScheduled || isRegOpen || isRegClosed;
  const canEditVoteClose = isDraft || isScheduled || isRegOpen || isRegClosed || isVotingOpen;

  const [regOpen, setRegOpen] = useState(formatDateTimeLocalInput(election.registration_opens_at));
  const [regClose, setRegClose] = useState(formatDateTimeLocalInput(election.registration_closes_at));
  const [voteOpen, setVoteOpen] = useState(formatDateTimeLocalInput(election.voting_opens_at));
  const [voteClose, setVoteClose] = useState(formatDateTimeLocalInput(election.voting_closes_at));
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validar orden básico en cliente
    const dRegOpen = new Date(regOpen);
    const dRegClose = new Date(regClose);
    const dVoteOpen = new Date(voteOpen);
    const dVoteClose = new Date(voteClose);

    if (!(dRegOpen < dRegClose && dRegClose <= dVoteOpen && dVoteOpen < dVoteClose)) {
      setError(
        'El orden cronológico es inválido: Inicio Registro < Fin Registro ≤ Inicio Votación < Fin Votación'
      );
      return;
    }

    if (!isDraft && (!reason || reason.trim().length < 10)) {
      setError(
        'Debe ingresar un motivo formal de al menos 10 caracteres que justifique la modificación del cronograma.'
      );
      return;
    }

    try {
      await onSave({
        registration_opens_at: dRegOpen.toISOString(),
        registration_closes_at: dRegClose.toISOString(),
        voting_opens_at: dVoteOpen.toISOString(),
        voting_closes_at: dVoteClose.toISOString(),
        reason: isDraft ? reason || undefined : reason,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error al actualizar el cronograma.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-xl border border-stone-300 shadow-2xl max-w-2xl w-full overflow-hidden my-8">
        {/* Cabecera */}
        <div className="bg-civic-navy-900 text-white px-6 py-4 flex items-center justify-between">
          <div>
            <h3 className="font-title text-base font-bold">
              Modificación Oficial de Cronograma Electoral
            </h3>
            <p className="text-xs text-stone-300 font-mono mt-0.5">
              Estado actual de la elección: <span className="font-bold text-seal-amber">{status}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-seal-crimson-light border border-seal-crimson text-seal-crimson-dark text-xs rounded-lg flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Inicio de Registro */}
            <div>
              <label className="block text-xs font-semibold text-civic-navy-900 mb-1">
                Inicio del Registro
                {!canEditRegOpen && (
                  <span className="ml-1 text-[11px] text-stone-400 font-normal">
                    (Bloqueado: fase iniciada/cerrada)
                  </span>
                )}
              </label>
              <div className="relative">
                <input
                  type="datetime-local"
                  value={regOpen}
                  onChange={(e) => setRegOpen(e.target.value)}
                  disabled={!canEditRegOpen}
                  className={`w-full text-xs font-mono rounded-lg border p-2.5 ${
                    canEditRegOpen
                      ? 'border-stone-300 focus:ring-2 focus:ring-civic-navy-800'
                      : 'bg-stone-100 border-stone-200 text-stone-400 cursor-not-allowed'
                  }`}
                  required
                />
                {!canEditRegOpen && (
                  <Lock className="w-4 h-4 text-stone-400 absolute right-3 top-3" />
                )}
              </div>
            </div>

            {/* Fin de Registro */}
            <div>
              <label className="block text-xs font-semibold text-civic-navy-900 mb-1">
                Fin del Registro
                {!canEditRegClose && (
                  <span className="ml-1 text-[11px] text-stone-400 font-normal">(Bloqueado)</span>
                )}
              </label>
              <div className="relative">
                <input
                  type="datetime-local"
                  value={regClose}
                  onChange={(e) => setRegClose(e.target.value)}
                  disabled={!canEditRegClose}
                  className={`w-full text-xs font-mono rounded-lg border p-2.5 ${
                    canEditRegClose
                      ? 'border-stone-300 focus:ring-2 focus:ring-civic-navy-800'
                      : 'bg-stone-100 border-stone-200 text-stone-400 cursor-not-allowed'
                  }`}
                  required
                />
                {!canEditRegClose && (
                  <Lock className="w-4 h-4 text-stone-400 absolute right-3 top-3" />
                )}
              </div>
            </div>

            {/* Inicio de Votación */}
            <div>
              <label className="block text-xs font-semibold text-civic-navy-900 mb-1">
                Inicio de la Votación
                {!canEditVoteOpen && (
                  <span className="ml-1 text-[11px] text-stone-400 font-normal">(Bloqueado)</span>
                )}
              </label>
              <div className="relative">
                <input
                  type="datetime-local"
                  value={voteOpen}
                  onChange={(e) => setVoteOpen(e.target.value)}
                  disabled={!canEditVoteOpen}
                  className={`w-full text-xs font-mono rounded-lg border p-2.5 ${
                    canEditVoteOpen
                      ? 'border-stone-300 focus:ring-2 focus:ring-civic-navy-800'
                      : 'bg-stone-100 border-stone-200 text-stone-400 cursor-not-allowed'
                  }`}
                  required
                />
                {!canEditVoteOpen && (
                  <Lock className="w-4 h-4 text-stone-400 absolute right-3 top-3" />
                )}
              </div>
            </div>

            {/* Fin de Votación */}
            <div>
              <label className="block text-xs font-semibold text-civic-navy-900 mb-1">
                Fin de la Votación
                {!canEditVoteClose && (
                  <span className="ml-1 text-[11px] text-stone-400 font-normal">(Bloqueado)</span>
                )}
              </label>
              <div className="relative">
                <input
                  type="datetime-local"
                  value={voteClose}
                  onChange={(e) => setVoteClose(e.target.value)}
                  disabled={!canEditVoteClose}
                  className={`w-full text-xs font-mono rounded-lg border p-2.5 ${
                    canEditVoteClose
                      ? 'border-stone-300 focus:ring-2 focus:ring-civic-navy-800'
                      : 'bg-stone-100 border-stone-200 text-stone-400 cursor-not-allowed'
                  }`}
                  required
                />
                {!canEditVoteClose && (
                  <Lock className="w-4 h-4 text-stone-400 absolute right-3 top-3" />
                )}
              </div>
            </div>
          </div>

          {/* Motivo de Auditoría */}
          <div>
            <label className="block text-xs font-semibold text-civic-navy-900 mb-1">
              Motivo Formal de la Modificación {isDraft ? '(Opcional en Borrador)' : '(Obligatorio)'}
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                isDraft
                  ? 'Notas internas sobre el cronograma...'
                  : 'Describa detalladamente la justificación legal o técnica para este cambio (mínimo 10 caracteres)...'
              }
              rows={3}
              className="w-full text-xs rounded-lg border border-stone-300 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
              required={!isDraft}
            />
          </div>

          {/* Botones de acción */}
          <div className="pt-3 border-t border-stone-200 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-stone-300 text-stone-700 text-xs font-semibold rounded-lg hover:bg-stone-100 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 bg-civic-navy-900 text-white text-xs font-semibold rounded-lg hover:bg-civic-navy-800 transition-colors shadow-sm disabled:opacity-50"
            >
              {isLoading ? 'Guardando...' : 'Aplicar Modificación Auditada'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
