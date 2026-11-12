import React, { useState } from 'react';
import { ImportIssue, DuplicateAdjudicationSuggestion } from '@votoseguro/api-client';
import { api } from '@/lib/api';

interface DuplicateAdjudicationDrawerProps {
  electionId: string;
  issue: ImportIssue | null;
  onClose: () => void;
  onResolved: () => void;
}

export const DuplicateAdjudicationDrawer: React.FC<DuplicateAdjudicationDrawerProps> = ({
  electionId,
  issue,
  onClose,
  onResolved,
}) => {
  const [reason, setReason] = useState('Verificación manual con documento de identidad');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<DuplicateAdjudicationSuggestion | null>(null);

  if (!issue) return null;

  const handleRequestAiOpinion = async () => {
    setAiLoading(true);
    setError(null);
    try {
      const res = await api.post<DuplicateAdjudicationSuggestion>(
        `/ai/duplicates/issues/${issue.id}/adjudicate`
      );
      setAiSuggestion(res);
      if (res.short_reason) {
        setReason(`[Sugerencia IA]: ${res.short_reason}`);
      }
    } catch (err: any) {
      setError(err.message || 'Error solicitando segunda opinión de IA.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleResolve = async (action: 'CONFIRM_DISTINCT' | 'BLOCK_NEW' | 'REMOVE_NEW') => {
    setError(null);
    if (!reason.trim()) {
      setError('Por favor indique el motivo o justificación del dictamen.');
      return;
    }

    try {
      setSubmitting(true);
      await api.post(`/elections/${electionId}/voters/duplicates/${issue.id}/resolve`, {
        action,
        reason: reason.trim(),
      });
      onResolved();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error al registrar el dictamen de duplicidad.');
    } finally {
      setSubmitting(false);
    }
  };

  const simPct = Math.round((issue.similarity_score || 0) * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/50 backdrop-blur-xs p-0 animate-in fade-in duration-150">
      <div className="bg-white h-full w-full max-w-lg shadow-2xl border-l border-slate-300 flex flex-col justify-between overflow-y-auto">
        {/* Encabezado */}
        <div className="px-6 py-5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <div className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase bg-amber-100 text-amber-800 mb-1">
              <span>IA-L2a • Detector de Duplicados</span>
            </div>
            <h3 className="font-serif font-bold text-lg text-civic-navy">
              Arbitraje de Posible Duplicidad
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-2xl font-bold"
          >
            &times;
          </button>
        </div>

        {/* Contenido comparativo lado a lado */}
        <div className="p-6 space-y-6 flex-1">
          {error && (
            <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
              {error}
            </div>
          )}

          {/* Indicador de Similitud */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-slate-700">Puntaje de Similitud Trigram:</div>
              <div className="text-2xs text-slate-500">
                Distancia Levenshtein:{' '}
                <span className="font-mono font-bold text-slate-700">{issue.edit_distance ?? 'N/A'}</span> caracteres
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-xl font-mono font-black ${simPct >= 70 ? 'text-red-600' : 'text-amber-600'}`}>
                {simPct}%
              </span>
            </div>
          </div>

          {/* Comparación lado a lado */}
          <div className="grid grid-cols-2 gap-4">
            {/* Registro Entrante / Candidato */}
            <div className="p-4 rounded-xl border-2 border-amber-300 bg-amber-50/40 space-y-3">
              <div className="text-2xs font-bold uppercase text-amber-800 tracking-wider">
                📥 Registro Evaluado
              </div>
              <div>
                <div className="text-2xs text-slate-500 font-semibold">Nombre Completo:</div>
                <div className="font-serif font-bold text-sm text-slate-900 mt-0.5">
                  {issue.candidate_voter_name || issue.raw_full_name}
                </div>
              </div>
              <div>
                <div className="text-2xs text-slate-500 font-semibold">Documento (CI):</div>
                <div className="font-mono text-xs font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-amber-200 inline-block mt-0.5">
                  {issue.document_id || 'N/A'}
                </div>
              </div>
              <div className="text-2xs text-slate-500">
                Fila de importación: <span className="font-mono">#{issue.row_number}</span>
              </div>
            </div>

            {/* Registro Existente en BD */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-3">
              <div className="text-2xs font-bold uppercase text-slate-600 tracking-wider">
                🏛️ Registro Pre-Existente
              </div>
              <div>
                <div className="text-2xs text-slate-500 font-semibold">Nombre Registrado:</div>
                <div className="font-serif font-bold text-sm text-slate-900 mt-0.5">
                  {issue.matched_voter_name || 'Votante en Padrón'}
                </div>
              </div>
              <div>
                <div className="text-2xs text-slate-500 font-semibold">Documento (CI):</div>
                <div className="font-mono text-xs font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200 inline-block mt-0.5">
                  {issue.matched_voter_document || 'N/A'}
                </div>
              </div>
              <div className="text-2xs text-slate-500">
                Estado: <span className="font-semibold text-emerald-700">EN PADRÓN</span>
              </div>
            </div>
          </div>

          {/* IA-L2b: Segunda Opinión de IA Local */}
          <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-indigo-950 flex items-center gap-1.5">
                <span>🤖</span> Segunda Opinión Asistida (IA-L2b)
              </span>
              <button
                type="button"
                onClick={handleRequestAiOpinion}
                disabled={aiLoading}
                className="px-3 py-1.5 bg-indigo-700 hover:bg-indigo-600 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
              >
                <span>{aiLoading ? '⏳' : '✨'}</span>
                <span>{aiLoading ? 'Evaluando...' : 'Solicitar Segunda Opinión IA'}</span>
              </button>
            </div>

            {aiSuggestion && (
              <div className="p-3 bg-white rounded-lg border border-indigo-200 text-xs space-y-2 animate-in fade-in">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-gray-500 uppercase">
                    Veredicto Sugerido:
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full font-bold text-[11px] ${
                      aiSuggestion.verdict === 'mismo'
                        ? 'bg-red-100 text-red-800 border border-red-200'
                        : aiSuggestion.verdict === 'distinto'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {aiSuggestion.verdict.toUpperCase()} (Confianza: {aiSuggestion.confidence_label})
                  </span>
                </div>

                <div className="text-gray-800 leading-relaxed text-[11px]">
                  <strong>Motivo IA:</strong> {aiSuggestion.short_reason}
                </div>

                <div className="text-[10px] text-gray-400 flex items-center justify-between pt-1 border-t border-gray-100">
                  <span>Fuente: {aiSuggestion.ai_source}</span>
                  <span className="font-semibold text-indigo-700">Decisión Humana Obligatoria</span>
                </div>
              </div>
            )}
          </div>

          {/* Formulario de Dictamen */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-700">
              Motivo o Justificación del Dictamen Humano:
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="Ej. Se verificó con documento de identidad y matrícula institucional que son dos personas homónimas distintas."
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-civic-navy/20 focus:border-civic-navy"
            />
          </div>
        </div>

        {/* Botones de Acción */}
        <div className="p-6 bg-slate-50 border-t border-slate-200 space-y-2">
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleResolve('CONFIRM_DISTINCT')}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition disabled:opacity-50 flex items-center justify-center space-x-2"
          >
            <span>✓ Confirmar que son personas distintas (Conservar ambos)</span>
          </button>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleResolve('BLOCK_NEW')}
              className="py-2.5 px-3 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white shadow-xs transition disabled:opacity-50"
            >
              🔒 Bloquear Registro Nuevo
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleResolve('REMOVE_NEW')}
              className="py-2.5 px-3 rounded-xl text-xs font-semibold bg-red-600 hover:bg-red-700 text-white shadow-xs transition disabled:opacity-50"
            >
              🗑️ Descartar / Eliminar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
