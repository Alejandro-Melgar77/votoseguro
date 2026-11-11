import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  UserPlus,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Building2,
  ArrowLeft,
  Users,
  Layers,
  FileCheck2,
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import type {
  SelfRegistrationInfoResponse,
  SelfRegistrationRequest,
  SelfRegistrationResponse,
} from '@votoseguro/api-client';

export const PublicSelfRegistrationPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();

  const [info, setInfo] = useState<SelfRegistrationInfoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [documentId, setDocumentId] = useState<string>('');
  const [fullName, setFullName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [selectedGroupId, setSelectedGroupId] = useState<string>('');
  const [selectedNodeId, setSelectedNodeId] = useState<string>('');

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<SelfRegistrationResponse | null>(null);

  const fetchInfo = async () => {
    if (!electionId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.get<SelfRegistrationInfoResponse>(
        `/public/elections/${electionId}/self-registration-info`
      );
      setInfo(data);
      if (data.groups && data.groups.length > 0) {
        setSelectedGroupId(data.groups[0].id);
        if (data.groups[0].nodes && data.groups[0].nodes.length > 0) {
          setSelectedNodeId(data.groups[0].nodes[0].id);
        }
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Error al cargar información de autoinscripción pública.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInfo();
  }, [electionId]);

  const handleGroupChange = (groupId: string) => {
    setSelectedGroupId(groupId);
    const grp = info?.groups.find((g) => g.id === groupId);
    if (grp && grp.nodes && grp.nodes.length > 0) {
      setSelectedNodeId(grp.nodes[0].id);
    } else {
      setSelectedNodeId('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!electionId || !documentId.trim() || !fullName.trim() || !selectedGroupId || !selectedNodeId) {
      setSubmitError('Por favor complete todos los campos obligatorios del formulario.');
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);

      const payload: SelfRegistrationRequest = {
        document_id: documentId.trim(),
        full_name: fullName.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
        group_id: selectedGroupId,
        node_id: selectedNodeId,
      };

      const result = await api.post<SelfRegistrationResponse>(
        `/public/elections/${electionId}/self-register`,
        payload
      );
      setSuccessResult(result);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError('Error al enviar la solicitud de autoinscripción.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const currentGroup = info?.groups.find((g) => g.id === selectedGroupId);

  return (
    <div className="min-h-screen bg-ballot-ivory-100 flex flex-col font-sans">
      <header className="bg-civic-navy-900 border-b border-civic-navy-800 text-white px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-seal-emerald/20 border border-seal-emerald/40 flex items-center justify-center text-seal-emerald font-bold">
              VS
            </div>
            <div>
              <h1 className="font-title text-base font-bold tracking-wide">VotoSeguro v2.0</h1>
              <p className="text-[11px] text-stone-300 font-sans">Portal de Autoinscripción Ciudadana</p>
            </div>
          </div>

          <Link
            to="/"
            className="text-xs text-stone-300 hover:text-white flex items-center space-x-1.5 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Inicio</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto p-6 md:p-8 space-y-6">
        {loading && (
          <div className="p-12 text-center text-xs font-mono text-stone-500">
            Cargando información de autoinscripción electoral...
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Inscripción No Disponible</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {info && !loading && (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-seal-emerald text-xs font-semibold">
                <UserPlus className="w-4 h-4" />
                <span>Modalidad Abierta con Aprobación (S2-10)</span>
              </div>
              <h2 className="font-title text-2xl font-bold text-civic-navy-900">{info.election_name}</h2>
              <p className="text-xs text-stone-600 max-w-xl mx-auto">
                Completa tus datos oficiales para solicitar la habilitación en el padrón electoral.
                Tu registro quedará pendiente de aprobación por el Administrador General antes del cierre de registro.
              </p>
            </div>

            {!info.is_open ? (
              <div className="p-6 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-900 space-y-2 text-center">
                <Clock className="w-8 h-8 text-amber-600 mx-auto" />
                <h3 className="font-bold text-sm">Fase de Autoinscripción Cerrada</h3>
                <p>
                  El periodo de registro para esta elección no se encuentra activo actualmente (Estado actual:{' '}
                  <span className="font-mono font-bold">{info.status}</span>).
                </p>
              </div>
            ) : successResult ? (
              /* Tarjeta de Confirmación Exitosa */
              <div className="bg-white border border-stone-300 rounded-2xl p-6 md:p-8 shadow-electoral space-y-6">
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-3">
                  <CheckCircle2 className="w-8 h-8 text-seal-emerald shrink-0" />
                  <div>
                    <h3 className="font-title text-base font-bold text-emerald-950">
                      SOLICITUD DE INSCRIPCIÓN REGISTRADA SATISFACTORIAMENTE
                    </h3>
                    <p className="text-xs text-emerald-800 mt-0.5">{successResult.message}</p>
                  </div>
                </div>

                <div className="bg-stone-50 border border-stone-200 rounded-xl p-5 space-y-3 text-xs font-mono">
                  <div className="flex justify-between border-b border-stone-200 pb-2">
                    <span className="text-stone-500">Documento de Identidad:</span>
                    <span className="font-bold text-stone-900">{successResult.document_id}</span>
                  </div>
                  <div className="flex justify-between border-b border-stone-200 pb-2">
                    <span className="text-stone-500">Nombre Completo:</span>
                    <span className="font-bold text-stone-900">{successResult.full_name}</span>
                  </div>
                  <div className="flex justify-between border-b border-stone-200 pb-2">
                    <span className="text-stone-500">Estado de la Solicitud:</span>
                    <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                      {successResult.status} (Pendiente de Aprobación)
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-stone-500">ID de Registro:</span>
                    <span className="text-stone-700">{successResult.voter_id}</span>
                  </div>
                </div>

                <div className="p-4 bg-stone-100 rounded-xl text-xs text-stone-700 space-y-1">
                  <p className="font-bold">¿Qué sucede a continuación?</p>
                  <p className="text-stone-600 text-[11px] leading-relaxed">
                    La comisión electoral o junta de administración verificará tu pertenencia a la unidad seleccionada.
                    Una vez aprobada tu solicitud, recibirás tu notificación de acreditación y formarás parte del padrón
                    electoral congelado por el Árbol de Merkle para la votación.
                  </p>
                </div>
              </div>
            ) : (
              /* Formulario de Registro */
              <div className="bg-white border border-stone-300 rounded-2xl p-6 md:p-8 shadow-electoral space-y-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                  {submitError && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                      <span>{submitError}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <label className="block font-bold text-stone-700 uppercase font-mono text-[11px] mb-1">
                        Cédula de Identidad / Documento *
                      </label>
                      <input
                        type="text"
                        required
                        value={documentId}
                        onChange={(e) => setDocumentId(e.target.value)}
                        placeholder="Ej. 1004523, 8934521"
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg font-mono focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                      />
                    </div>

                    <div>
                      <label className="block font-bold text-stone-700 uppercase font-mono text-[11px] mb-1">
                        Nombres y Apellidos Completos *
                      </label>
                      <input
                        type="text"
                        required
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Ej. Carlos Mendoza Quiroga"
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                      />
                    </div>

                    <div>
                      <label className="block font-bold text-stone-700 uppercase font-mono text-[11px] mb-1">
                        Correo Electrónico (Notificaciones)
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="ejemplo@institucion.edu"
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                      />
                    </div>

                    <div>
                      <label className="block font-bold text-stone-700 uppercase font-mono text-[11px] mb-1">
                        Teléfono Celular (Opcional)
                      </label>
                      <input
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="+591 70000000"
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                      />
                    </div>
                  </div>

                  <div className="border-t border-stone-200 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <label className="block font-bold text-stone-700 uppercase font-mono text-[11px] mb-1">
                        Sector / Grupo Electoral *
                      </label>
                      <select
                        value={selectedGroupId}
                        onChange={(e) => handleGroupChange(e.target.value)}
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg font-mono focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                      >
                        {info.groups.map((grp) => (
                          <option key={grp.id} value={grp.id}>
                            {grp.name} ({grp.code})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block font-bold text-stone-700 uppercase font-mono text-[11px] mb-1">
                        Unidad Académica / Nodo Organizacional *
                      </label>
                      <select
                        value={selectedNodeId}
                        onChange={(e) => setSelectedNodeId(e.target.value)}
                        disabled={!currentGroup || !currentGroup.nodes || currentGroup.nodes.length === 0}
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg font-mono focus:outline-hidden focus:ring-2 focus:ring-seal-emerald disabled:opacity-50"
                      >
                        {currentGroup?.nodes.map((nd) => (
                          <option key={nd.id} value={nd.id}>
                            {nd.name} ({nd.code}) — Ruta: {nd.path}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-3 bg-civic-navy-900 text-white rounded-xl text-xs font-bold hover:bg-civic-navy-800 flex items-center justify-center space-x-2 transition-colors disabled:opacity-50 shadow-md"
                    >
                      <FileCheck2 className={`w-4 h-4 ${submitting ? 'animate-spin' : ''}`} />
                      <span>{submitting ? 'Enviando Solicitud...' : 'Enviar Solicitud de Autoinscripción'}</span>
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-stone-200 py-4 text-center text-xs text-stone-500 font-mono">
        VotoSeguro v2.0 • Autoinscripción Electoral con Aprobación Institucional
      </footer>
    </div>
  );
};
