import React, { useEffect, useState } from 'react';
import {
  Camera,
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  X,
  Upload,
  Sparkles,
  ArrowRight,
  EyeOff,
} from 'lucide-react';
import { api } from '@/lib/api';

interface BiometricSelfieVerificationModalProps {
  electionId: string;
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
  onVerifiedSuccess: () => void;
  onContinueWithFallback: () => void;
}

export const BiometricSelfieVerificationModal: React.FC<BiometricSelfieVerificationModalProps> = ({
  electionId,
  documentId,
  isOpen,
  onClose,
  onVerifiedSuccess,
  onContinueWithFallback,
}) => {
  const [step, setStep] = useState<'consent' | 'capture' | 'verdict'>('consent');
  const [consentGiven, setConsentGiven] = useState(false);
  const [selfieB64, setSelfieB64] = useState<string>('');
  const [idCardB64, setIdCardB64] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verdictData, setVerdictData] = useState<any | null>(null);

  useEffect(() => {
    if (!isOpen) { setSelfieB64(''); setIdCardB64(''); setConsentGiven(false); setVerdictData(null); setStep('consent'); }
  }, [isOpen]);
  if (!isOpen) return null;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>, target: 'selfie' | 'id') => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Use una imagen JPG, PNG o WebP.'); return;
    }
    if (file.size > 3 * 1024 * 1024) {
      setError('La imagen no debe superar los 3 MB.');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      if (target === 'selfie') setSelfieB64(result);
      else setIdCardB64(result);
      setError(null);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmitVerification = async () => {
    if (!selfieB64 || !idCardB64) {
      setError('Por favor proporcione tanto la selfie como la fotografía de su documento de identidad.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await api.post<any>('/ai/biometric/verify', {
        election_id: electionId,
        document_id: documentId,
        consent_accepted: consentGiven,
        selfie_base64: selfieB64,
        id_card_base64: idCardB64,
        use_fallback_code: false,
      });

      setVerdictData(data);
      setStep('verdict');

      // Purga explícita en cliente
      setSelfieB64('');
      setIdCardB64('');
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Error al procesar la verificación facial asistida con Gemini.'
      );
    } finally {
      setSelfieB64(''); setIdCardB64('');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-stone-200 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Cabecera */}
        <div className="bg-civic-navy-950 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h3 className="font-bold font-serif text-sm">
              Verificación Facial Asistida con Gemini (IA-E3)
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* PASO 1: CONSENTIMIENTO INFORMADO */}
        {step === 'consent' && (
          <div className="p-6 space-y-5 text-xs">
            <div className="p-4 bg-amber-50/80 border border-amber-200 rounded-xl space-y-2 text-stone-800">
              <div className="flex items-center gap-1.5 font-bold text-amber-900">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                Consentimiento de Procesamiento Biométrico en Memoria (Invariante #15)
              </div>
              <p className="leading-relaxed text-stone-700">
                Esta verificación es <strong>totalmente opcional</strong>. Las imágenes de su rostro y documento se
                envían a Gemini para cotejar los rasgos. Nuestra aplicación procesa las imágenes temporalmente y{' '}
                <strong>jamás se guardan en el servidor, base de datos ni almacenamiento permanente</strong>.
              </p>
              <p className="text-stone-600">
                Siempre tiene garantizado el derecho de optar por la alternativa de verificación por código o mesa electoral.
              </p>
            </div>

            <label className="flex items-start gap-3 p-3 bg-stone-50 border border-stone-200 rounded-xl cursor-pointer hover:bg-stone-100/60 transition-colors">
              <input
                type="checkbox"
                checked={consentGiven}
                onChange={(e) => setConsentGiven(e.target.checked)}
                className="mt-0.5 rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
              />
              <span className="text-stone-800 font-medium leading-tight">
                Doy mi consentimiento explícito e informado para procesar temporalmente mis rasgos faciales en memoria
                conforme a la normativa de protección de datos personales.
              </span>
            </label>

            <div className="pt-2 flex flex-col sm:flex-row items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  onContinueWithFallback();
                  onClose();
                }}
                className="w-full sm:w-auto px-4 py-2 rounded-lg border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium transition-colors"
              >
                Omitir y Usar Verificación por Código
              </button>
              <button
                type="button"
                disabled={!consentGiven}
                onClick={() => setStep('capture')}
                className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-stone-300 text-white font-semibold transition-colors flex items-center justify-center gap-1.5"
              >
                Continuar a Captura
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* PASO 2: CAPTURA O CARGA */}
        {step === 'capture' && (
          <div className="p-6 space-y-4 text-xs">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                <div>{error}</div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Selfie */}
              <div className="border border-stone-200 rounded-xl p-3 bg-stone-50 text-center space-y-2">
                <p className="font-bold text-stone-800">1. Fotografía Selfie</p>
                {selfieB64 ? (
                  <div className="relative">
                    <img
                      src={selfieB64}
                      alt="Selfie"
                      className="w-full h-32 object-cover rounded-lg border border-stone-300"
                    />
                    <button
                      onClick={() => setSelfieB64('')}
                      className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-1"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center h-32 border-2 border-dashed border-stone-300 rounded-lg cursor-pointer hover:bg-stone-100/60 transition-colors">
                    <Camera className="w-6 h-6 text-stone-400 mb-1" />
                    <span className="text-[11px] text-stone-600 font-medium">Subir foto selfie</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      capture="user"
                      onChange={(e) => handleFileUpload(e, 'selfie')}
                      className="hidden"
                    />
                  </label>
                )}
              </div>

              {/* Cédula */}
              <div className="border border-stone-200 rounded-xl p-3 bg-stone-50 text-center space-y-2">
                <p className="font-bold text-stone-800">2. Foto de Cédula</p>
                {idCardB64 ? (
                  <div className="relative">
                    <img
                      src={idCardB64}
                      alt="Cédula"
                      className="w-full h-32 object-cover rounded-lg border border-stone-300"
                    />
                    <button
                      onClick={() => setIdCardB64('')}
                      className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-1"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center h-32 border-2 border-dashed border-stone-300 rounded-lg cursor-pointer hover:bg-stone-100/60 transition-colors">
                    <Upload className="w-6 h-6 text-stone-400 mb-1" />
                    <span className="text-[11px] text-stone-600 font-medium">Subir foto cédula</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      capture="environment"
                      onChange={(e) => handleFileUpload(e, 'id')}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">

              <span className="text-[10px] text-stone-400 flex items-center gap-1">
                <EyeOff className="w-3 h-3" /> Cero almacenamiento
              </span>
            </div>

            <div className="pt-3 flex items-center justify-end gap-2 border-t border-stone-100">
              <button
                type="button"
                onClick={() => setStep('consent')}
                className="px-3 py-1.5 rounded-lg border border-stone-300 text-stone-700 hover:bg-stone-50"
              >
                Atrás
              </button>
              <button
                type="button"
                onClick={handleSubmitVerification}
                disabled={loading || !selfieB64 || !idCardB64}
                className="px-4 py-2 rounded-lg bg-civic-navy-950 hover:bg-civic-navy-900 disabled:bg-stone-300 text-white font-semibold flex items-center gap-2"
              >
                <Sparkles className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Analizando en memoria con Gemini...' : 'Cotejar con Gemini'}
              </button>
            </div>
          </div>
        )}

        {/* PASO 3: VEREDICTO DE GEMINI */}
        {step === 'verdict' && verdictData && (
          <div className="p-6 space-y-4 text-xs">
            <div
              className={`p-4 rounded-xl border flex items-start gap-3 ${
                verdictData.match_verdict === 'MATCH_PROBABLE'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                  : verdictData.match_verdict === 'MISMATCH'
                  ? 'bg-red-50 border-red-200 text-red-950'
                  : 'bg-amber-50 border-amber-200 text-amber-950'
              }`}
            >
              {verdictData.match_verdict === 'MATCH_PROBABLE' ? (
                <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <p className="font-bold text-sm">
                  Veredicto:{' '}
                  {verdictData.match_verdict === 'MATCH_PROBABLE'
                    ? 'COINCIDENCIA PROBABLE'
                    : verdictData.match_verdict === 'MISMATCH'
                    ? 'DISCREPANCIA FACIAL'
                    : 'INCONCLUSO'}
                </p>
                <p>{verdictData.explanation_es}</p>
                <p className="text-[10px] opacity-80 pt-1">
                  Confianza: {verdictData.confidence_band} • Motor: {verdictData.ai_source}
                </p>
              </div>
            </div>

            <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg text-stone-600 space-y-1">
              <p className="font-semibold text-stone-700">Salvaguarda Legal y Técnica:</p>
              <p>{verdictData.liveness_disclaimer}</p>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              {verdictData.match_verdict === 'MATCH_PROBABLE' ? (
                <button
                  type="button"
                  onClick={() => {
                    onVerifiedSuccess();
                    onClose();
                  }}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Aceptar y Continuar Registro
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    onContinueWithFallback();
                    onClose();
                  }}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold"
                >
                  Continuar con Verificación por Código
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
