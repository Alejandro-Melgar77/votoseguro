import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  Clock,
  UserCheck,
  CheckCircle2,
  Building2,
  Layers,
  ArrowRight,
  Vote,
  Sparkles,
  Printer,
  ChevronRight,
  Lock,
} from 'lucide-react';
import { PublicRegistrationInfo, PublicActivationResponse } from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { formatElectoralDateTime } from '@/lib/timezone';
import { IdCardOcrScannerModal } from '@/components/electoral/IdCardOcrScannerModal';
import { ElectoralFaqAssistantWidget } from '@/components/electoral/ElectoralFaqAssistantWidget';

export const PublicVoterRegistrationPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();

  const [loading, setLoading] = useState(true);
  const [linkInfo, setLinkInfo] = useState<PublicRegistrationInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Formulario de Activación
  const [documentId, setDocumentId] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showOcrModal, setShowOcrModal] = useState(false);

  // Certificado de Activación
  const [activationResult, setActivationResult] = useState<PublicActivationResponse | null>(null);

  useEffect(() => {
    if (!token) {
      setLoadError('El enlace de registro no es válido o está incompleto.');
      setLoading(false);
      return;
    }

    const fetchInfo = async () => {
      try {
        setLoading(true);
        setLoadError(null);
        const data = await api.get<PublicRegistrationInfo>(`/register/${token}`);
        setLinkInfo(data);
      } catch (err: any) {
        setLoadError(err.message || 'No fue posible validar el enlace de registro.');
      } finally {
        setLoading(false);
      }
    };

    fetchInfo();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!documentId.trim()) {
      setSubmitError('Debe ingresar su Cédula de Identidad o Documento Oficial.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await api.post<PublicActivationResponse>(`/register/${token}`, {
        document_id: documentId.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
      });
      setActivationResult(res);
    } catch (err: any) {
      setSubmitError(err.message || 'Error al procesar la activación de su registro.');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-stone-100 flex flex-col justify-between font-sans text-stone-900">
      {/* Barra Superior Cívica */}
      <header className="bg-civic-navy-900 text-stone-100 border-b border-stone-800 shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center font-bold text-white shadow-sm">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold tracking-tight text-base font-serif">VotoSeguro v1.0</span>
              <span className="block text-2xs text-stone-400 font-mono">PORTAL PÚBLICO DE ACTIVACIÓN ELECTORAL</span>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs text-stone-300">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-2xs">Criptográficamente Auditado</span>
          </div>
        </div>
      </header>

      {/* Contenido Central */}
      <main className="flex-1 max-w-xl w-full mx-auto px-4 py-8">
        {loading && (
          <div className="bg-white border border-stone-300 rounded-xl p-8 text-center shadow-sm space-y-4">
            <div className="w-10 h-10 border-4 border-civic-navy-900 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm font-semibold text-stone-600">Verificando enlace de registro oficial...</p>
          </div>
        )}

        {!loading && loadError && (
          <div className="bg-white border border-red-300 rounded-xl p-8 text-center shadow-sm space-y-4">
            <div className="w-12 h-12 bg-red-100 text-red-700 rounded-full flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-stone-900">Enlace No Disponible</h2>
            <p className="text-sm text-stone-600 max-w-md mx-auto">{loadError}</p>
            <div className="pt-4">
              <Link
                to="/"
                className="inline-flex items-center space-x-2 text-xs font-bold text-civic-navy-900 hover:underline"
              >
                <span>Volver al Portal Principal</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        )}

        {!loading && !loadError && linkInfo && !activationResult && (
          <div className="bg-white border border-stone-300 rounded-xl shadow-md overflow-hidden">
            {/* Cabecera de la Elección */}
            <div className="bg-stone-50 border-b border-stone-200 p-6 space-y-3">
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-emerald-100 text-emerald-900 rounded-full text-2xs font-bold">
                <Clock className="w-3 h-3 text-emerald-700" />
                <span>REGISTRO CIUDADANO ABIERTO</span>
              </div>
              <h1 className="text-xl font-bold font-serif text-stone-900">{linkInfo.election_name}</h1>
              <div className="text-xs text-stone-600 space-y-1">
                <div className="flex items-center space-x-2">
                  <Building2 className="w-3.5 h-3.5 text-stone-400" />
                  <span className="font-semibold text-stone-800">{linkInfo.organization_name}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Layers className="w-3.5 h-3.5 text-stone-400" />
                  <span>Grupo Objetivo: <strong className="text-stone-800">{linkInfo.group_name}</strong></span>
                </div>
                {linkInfo.node_name && (
                  <div className="flex items-center space-x-2">
                    <span className="w-3.5 inline-block text-center text-stone-400">•</span>
                    <span>Segmento: <strong className="text-stone-800">{linkInfo.node_name}</strong> ({linkInfo.node_path})</span>
                  </div>
                )}
              </div>

              <div className="pt-2 text-2xs font-mono text-stone-500">
                Plazo límite de empadronamiento: {formatElectoralDateTime(linkInfo.closes_at)}
              </div>
            </div>

            {/* Formulario de Activación */}
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <h3 className="text-sm font-bold text-stone-900 flex items-center space-x-2">
                  <UserCheck className="w-4 h-4 text-civic-navy-900" />
                  <span>Confirmación de Identidad Ciudadana</span>
                </h3>
                <p className="text-xs text-stone-500 mt-1">
                  Ingrese su Cédula de Identidad para activar su condición de votante habilitado en el padrón electoral oficial.
                </p>
              </div>

              {submitError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>{submitError}</div>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-bold text-stone-700">
                      Cédula de Identidad (CI / DNI) <span className="text-red-500">*</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowOcrModal(true)}
                      className="text-xs text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 transition-colors"
                    >
                      <span>📷</span> Escanear Cédula (OCR Local + IA-L3)
                    </button>
                  </div>
                  <input
                    type="text"
                    required
                    value={documentId}
                    onChange={(e) => setDocumentId(e.target.value)}
                    placeholder="Ej. CI-8001001 o 10293847"
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-civic-navy-900"
                  />
                  <span className="text-2xs text-stone-400 block mt-1">
                    Debe coincidir exactamente con el documento provisto a la institución.
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-bold text-stone-700 mb-1">
                    Correo Electrónico (Opcional para recibir credencial)
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="su-correo@ejemplo.com"
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-civic-navy-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-stone-700 mb-1">
                    Teléfono Celular (Opcional)
                  </label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+591 70000000"
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-civic-navy-900"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-2.5 px-4 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-lg text-sm font-bold shadow transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Validando y Activando...</span>
                    </>
                  ) : (
                    <>
                      <span>Activar Mi Registro Electoral</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 text-2xs text-stone-500 space-y-1">
                <div className="font-semibold text-stone-700 flex items-center space-x-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  <span>Garantía de Soberanía Electoral</span>
                </div>
                <p>
                  Al activar su registro, su inclusión quedará sellada en el padrón electoral definitivo con cálculo canónico de huella criptográfica (SHA-256).
                </p>
              </div>
            </form>
          </div>
        )}

        {/* Certificado de Activación Exitoso */}
        {activationResult && (
          <div className="bg-white border border-emerald-300 rounded-xl shadow-lg overflow-hidden space-y-6 p-6">
            <div className="text-center space-y-2">
              <div className="w-14 h-14 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto shadow-sm">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold font-serif text-stone-900">
                Certificado Digital de Empadronamiento Activo
              </h2>
              <p className="text-xs text-stone-600">
                Su condición de votante ha sido activada oficialmente en el padrón electoral.
              </p>
            </div>

            {/* Tarjeta de Datos del Votante */}
            <div className="bg-stone-50 border border-stone-200 rounded-lg p-4 space-y-3 font-mono text-xs">
              <div className="flex justify-between border-b border-stone-200 pb-2">
                <span className="text-stone-500 font-sans">Votante Habilitado:</span>
                <span className="font-bold text-stone-900">{activationResult.full_name}</span>
              </div>
              <div className="flex justify-between border-b border-stone-200 pb-2">
                <span className="text-stone-500 font-sans">Documento de Identidad:</span>
                <span className="font-bold text-stone-900">{activationResult.document_id}</span>
              </div>
              <div className="flex justify-between border-b border-stone-200 pb-2">
                <span className="text-stone-500 font-sans">Grupo Electoral:</span>
                <span className="font-semibold text-stone-800">{activationResult.group_name}</span>
              </div>
              <div className="flex justify-between border-b border-stone-200 pb-2">
                <span className="text-stone-500 font-sans">Rama Territorial / Nodo:</span>
                <span className="font-semibold text-stone-800">{activationResult.node_path}</span>
              </div>
              <div className="flex justify-between border-b border-stone-200 pb-2">
                <span className="text-stone-500 font-sans">Fecha y Hora de Activación:</span>
                <span className="text-stone-700">{formatElectoralDateTime(activationResult.activated_at)}</span>
              </div>
              <div className="flex justify-between items-center pt-1">
                <span className="text-stone-500 font-sans">Estado del Votante:</span>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-900 font-bold rounded text-2xs">
                  {activationResult.status}
                </span>
              </div>
            </div>

            {/* Aviso de Próximo Paso */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-xs text-amber-900 space-y-2">
              <div className="font-bold flex items-center space-x-1.5">
                <Sparkles className="w-4 h-4 text-amber-700" />
                <span>¿Cómo emitir su sufragio en la jornada electoral?</span>
              </div>
              <p className="text-amber-800">
                Al abrirse la votación oficial (<strong>VOTING_OPEN</strong>), el sistema emitirá de forma automática su <strong>Credencial Personal de Votación</strong> de un solo uso (código de seguridad). Con su CI y dicho código podrá ingresar a la Cabina Electoral Digital en <strong>/vote</strong> para votar en su papeleta correspondiente.
              </p>
            </div>

            {/* Botones de Acción */}
            <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
              <button
                type="button"
                onClick={handlePrint}
                className="w-full sm:w-1/2 py-2.5 px-4 bg-stone-200 hover:bg-stone-300 text-stone-800 rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-colors"
              >
                <Printer className="w-4 h-4" />
                <span>Imprimir / Guardar Certificado</span>
              </button>
              <Link
                to="/vote"
                className="w-full sm:w-1/2 py-2.5 px-4 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-colors shadow"
              >
                <Vote className="w-4 h-4" />
                <span>Ir a la Cabina de Votación</span>
              </Link>
            </div>
          </div>
        )}
      </main>

      {/* Pie de Página */}
      <footer className="bg-white border-t border-stone-200 py-4 text-center text-xs text-stone-500">
        <p>VotoSeguro v2.0 — Plataforma Soberana de Sufragio Electrónico Multi-inquilino</p>
        <p className="text-2xs text-stone-400 mt-0.5">Diseñado con rigor criptográfico e integridad auditable</p>
      </footer>

      {/* Modal OCR de Cédula */}
      <IdCardOcrScannerModal
        isOpen={showOcrModal}
        onClose={() => setShowOcrModal(false)}
        electionId={linkInfo?.election_id}
        onConfirm={(data) => {
          setDocumentId(data.ci);
        }}
      />

      {/* Asistente Electoral Oficial RAG */}
      <ElectoralFaqAssistantWidget electionId={linkInfo?.election_id} />
    </div>
  );
};
