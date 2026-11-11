import React, { useState } from 'react';
import { Election } from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { CryptographicHashBadge } from './CryptographicHashBadge';

interface PublicationCeremonyModalProps {
  election: Election;
  onClose: () => void;
  onPublished: (updatedElection: Election) => void;
}

export const PublicationCeremonyModal: React.FC<PublicationCeremonyModalProps> = ({
  election,
  onClose,
  onPublished,
}) => {
  const [publishing, setPublishing] = useState(false);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [publishedElection, setPublishedElection] = useState<Election | null>(null);

  const handlePublish = async () => {
    setErrorDetail(null);
    try {
      setPublishing(true);
      const res = await api.post<Election>(`/elections/${election.id}/publish`);
      setPublishedElection(res);
      onPublished(res);
    } catch (err: any) {
      setErrorDetail(err.message || 'Error durante la ceremonia de publicación.');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-300 w-full max-w-lg overflow-hidden">
        {/* Cabecera Ceremonial */}
        <div className="bg-civic-navy text-white px-6 py-5 text-center relative">
          <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-amber-400/20 border border-amber-400/40 flex items-center justify-center text-2xl">
            🏛️
          </div>
          <h3 className="font-serif text-xl font-bold tracking-tight">
            Ceremonia de Publicación y Congelamiento
          </h3>
          <p className="text-xs text-slate-300 mt-1">
            Emisión de Sello Criptográfico Inmutable (<span className="font-mono">config_hash</span>)
          </p>
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-300 hover:text-white text-lg font-bold"
          >
            &times;
          </button>
        </div>

        <div className="p-6 space-y-5">
          {publishedElection ? (
            /* Pantalla de Éxito y Sello Criptográfico */
            <div className="text-center space-y-4 py-2">
              <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-3xl shadow-inner">
                ✓
              </div>
              <div>
                <h4 className="font-serif text-lg font-black text-slate-900">
                  ¡Elección Publicada Exitosamente!
                </h4>
                <p className="text-xs text-slate-600 max-w-sm mx-auto mt-1">
                  La estructura electoral ha sido sellada matemáticamente. El estado de la elección avanzó a{' '}
                  <span className="font-bold text-civic-navy">{publishedElection.status}</span>.
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-left space-y-2">
                <div className="text-2xs font-bold text-slate-500 uppercase tracking-wider">
                  Hash Criptográfico de Configuración (SHA-256):
                </div>
                {publishedElection.config_hash && (
                  <CryptographicHashBadge
                    hash={publishedElection.config_hash}
                    label="config_hash"
                  />
                )}
                <div className="text-2xs text-slate-500 italic mt-2">
                  Cualquier intento posterior de modificar grupos, niveles, nodos, cargos o candidatos será rechazado con HTTP 409 Conflict.
                </div>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold bg-civic-navy text-white hover:bg-slate-800 transition"
              >
                Entendido y Continuar
              </button>
            </div>
          ) : (
            /* Checklist de Validación y Advertencia Solemne */
            <>
              {errorDetail && (
                <div className="p-3.5 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs space-y-1">
                  <div className="font-bold flex items-center space-x-1">
                    <span>⚠️ Validación de Consistencia Fallida:</span>
                  </div>
                  <p className="leading-relaxed">{errorDetail}</p>
                </div>
              )}

              <div className="space-y-2.5">
                <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Checklist de Consistencia Electoral (6 Reglas):
                </div>
                <div className="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-3.5 rounded-xl border border-slate-200 font-sans">
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span>Elección en estado Borrador (<code className="font-mono text-2xs">DRAFT</code>).</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span>Cronograma vigente con fechas cronológicas ordenadas.</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span>Grupos de votantes con jerarquías y nodos creados.</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span>Cargos en disputa asociados a sus niveles de alcance.</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span>Cobertura total de candidatos en todas las circunscripciones.</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span>Consistencia de profundidad de padrón pre-cargado.</span>
                  </div>
                </div>
              </div>

              {/* Advertencia Solemne */}
              <div className="p-3.5 bg-amber-50 border-l-4 border-amber-500 rounded-r-xl text-xs text-amber-900 space-y-1">
                <div className="font-bold flex items-center space-x-1">
                  <span>🔒 Advertencia de Inmutabilidad Criptográfica</span>
                </div>
                <p className="leading-relaxed">
                  Al confirmar, el sistema serializará toda la arquitectura electoral y emitirá el{' '}
                  <strong className="font-mono">config_hash</strong> SHA-256 oficial. A partir de este momento,
                  ningún grupo, nivel, nodo, cargo ni candidato podrá ser modificado o eliminado jamás.
                </p>
              </div>

              <div className="pt-2 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 text-xs font-semibold text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={publishing}
                  onClick={handlePublish}
                  className="px-5 py-2.5 text-xs font-bold text-white bg-civic-navy rounded-xl hover:bg-slate-800 disabled:opacity-50 transition shadow-sm flex items-center space-x-2"
                >
                  <span>{publishing ? 'Sellando Estructura...' : 'Publicar y Congelar Estructura'}</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
