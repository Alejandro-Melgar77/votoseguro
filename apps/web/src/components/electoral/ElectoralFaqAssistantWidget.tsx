/**
 * Widget Flotante del Asistente Electoral Oficial RAG (IA-L5).
 * Basado estrictamente en los 12 fragmentos de los manuales de VotoSeguro.
 * REGLA DE PRIVACIDAD (Sección 7.3): Se oculta automáticamente dentro de la papeleta activa.
 */
import React, { useState } from 'react';
import { api } from '../../lib/api';
import { RagAssistantResponse } from '@votoseguro/api-client';

interface ElectoralFaqAssistantWidgetProps {
  isVotingStep?: boolean;
  electionId?: string;
}

const QUICK_QUESTIONS = [
  '¿Cómo verifico mi comprobante de voto?',
  '¿Cómo se garantiza el secreto del voto?',
  '¿Qué significa voto en blanco y nulo?',
  '¿Cómo funciona la inclusión con Árbol de Merkle?',
  '¿Cómo funciona la cabina de voz accesible?',
];

export const ElectoralFaqAssistantWidget: React.FC<ElectoralFaqAssistantWidgetProps> = ({
  isVotingStep = false,
  electionId,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RagAssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Invariante de Privacidad (Sección 7.3): Desmontar si el votante está en el paso de votación
  if (isVotingStep) {
    return null;
  }

  const handleAsk = async (questionToAsk: string) => {
    const q = questionToAsk.trim();
    if (!q) return;

    setQuery(q);
    setLoading(true);
    setError(null);

    try {
      const res = await api.post<RagAssistantResponse>('/ai/assistant/ask', {
        question: q,
        context_role: 'VOTER',
        election_id: electionId || null,
      });
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'Error consultando al Asistente Electoral.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Botón Flotante */}
      <div className="fixed bottom-5 right-5 z-40">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="bg-[#0B132B] hover:bg-[#162550] text-white px-4 py-3 rounded-full shadow-2xl flex items-center gap-2.5 border border-emerald-500/40 transition-all hover:scale-105"
        >
          <span className="text-xl">🤖</span>
          <span className="text-xs font-semibold">Ayuda Electoral (RAG)</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        </button>
      </div>

      {/* Panel Lateral / Drawer */}
      {isOpen && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl border-l border-gray-200 flex flex-col animate-in slide-in-from-right duration-200">
          {/* Header */}
          <div className="bg-[#0B132B] text-white p-4 flex items-center justify-between border-b border-gray-800">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                📖
              </div>
              <div>
                <h3 className="font-bold text-sm">Asistente Electoral Oficial</h3>
                <p className="text-[11px] text-gray-300">RAG Oficial sobre Manuales de VotoSeguro (IA-L5)</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-white p-1 rounded font-bold"
            >
              ✕
            </button>
          </div>

          {/* Contenido */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs text-gray-700">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-blue-900 leading-relaxed text-[11px]">
              <strong>💡 Asistente Estrictamente Documental:</strong> Responde exclusivamente con base en los
              manuales y procedimientos auditados de VotoSeguro. No emite opiniones políticas ni predicciones.
            </div>

            {/* Preguntas Frecuentes Rápidas */}
            <div>
              <span className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Consultas Rápidas en 1 Clic
              </span>
              <div className="flex flex-col gap-1.5">
                {QUICK_QUESTIONS.map((qq, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleAsk(qq)}
                    className="text-left px-3 py-2 rounded-lg bg-gray-50 hover:bg-emerald-50 hover:border-emerald-300 border border-gray-200 text-gray-800 text-xs transition-colors flex items-center justify-between group"
                  >
                    <span>{qq}</span>
                    <span className="text-gray-400 group-hover:text-emerald-600 font-bold">→</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Resultado */}
            {loading && (
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 flex items-center justify-center gap-2 text-gray-600">
                <span className="animate-spin text-base">⏳</span>
                <span>Consultando base documental oficial...</span>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl">
                {error}
              </div>
            )}

            {response && !loading && (
              <div className="space-y-3">
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                    <span className="font-semibold text-gray-900 text-[11px] uppercase tracking-wide">
                      Respuesta Fundamentada
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                        response.answered_from_docs
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {response.answered_from_docs ? 'Manual Oficial' : 'Derivado a Soporte'}
                    </span>
                  </div>

                  <p className="text-xs text-gray-800 leading-relaxed whitespace-pre-line">
                    {response.answer}
                  </p>

                  {/* Citas Oficiales */}
                  {response.citations.length > 0 && (
                    <div className="pt-2 border-t border-gray-200 space-y-1.5">
                      <span className="block text-[11px] font-semibold text-gray-600">
                        📚 Fuentes Documentales Oficiales:
                      </span>
                      {response.citations.map((c, i) => (
                        <div key={i} className="p-2 rounded bg-white border border-gray-200 text-[11px]">
                          <strong className="text-emerald-700 font-mono block">{c.doc_id}: {c.title}</strong>
                          <span className="text-gray-600 italic">"{c.excerpt}"</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {response.escalate_to_support && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-[11px]">
                      ⚠️ <strong>Mesa de Ayuda Humana:</strong> Comuníquese con la Comisión Electoral institucional
                      para resolver esta duda presencial o telefónicamente.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Formulario de Pregunta Libre */}
          <div className="p-3 border-t border-gray-200 bg-gray-50">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAsk(query);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Escriba su consulta operativa..."
                className="flex-1 text-xs px-3 py-2 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-3.5 py-2 bg-[#0B132B] hover:bg-[#162550] text-white rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
              >
                Preguntar
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
