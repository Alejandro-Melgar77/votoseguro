import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  CheckCircle2,
  Clock,
  Building2,
  Lock,
  ArrowLeft,
  Copy,
  Check,
  FileCheck2,
  Binary,
  HelpCircle,
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';

interface ReceiptVerificationResponse {
  verified: boolean;
  status: string;
  receipt_hash: string;
  election_id: string;
  election_name: string;
  organization_name?: string;
  cast_at: string;
  chain_proof?: {
    chain_index: number;
    prev_hash: string;
    vote_hash: string;
    chain_intact: boolean;
  };
  message: string;
}

export const PublicReceiptVerifierPage: React.FC = () => {
  const { receiptHash: urlReceiptHash } = useParams<{ receiptHash?: string }>();
  const [searchParams] = useSearchParams();

  const [receiptInput, setReceiptInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ReceiptVerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const initialHash = urlReceiptHash || searchParams.get('hash') || '';

  const handleVerify = async (hashToVerify?: string) => {
    const hash = (hashToVerify || receiptInput).trim();
    if (!hash) return;

    try {
      setLoading(true);
      setError(null);
      setResult(null);
      const data = await api.get<ReceiptVerificationResponse>(`/receipts/${encodeURIComponent(hash)}`);
      setResult(data);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        setError('El código de comprobante no existe en los registros de la urna electoral.');
      } else {
        setError(err.message || 'Error al verificar el comprobante criptográfico.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialHash) {
      setReceiptInput(initialHash);
      handleVerify(initialHash);
    }
  }, [initialHash]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-ballot-ivory-100 flex flex-col font-sans">
      {/* Barra superior de soberanía cívica */}
      <header className="bg-civic-navy-900 border-b border-civic-navy-800 text-white px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-seal-emerald/20 border border-seal-emerald/40 flex items-center justify-center text-seal-emerald font-bold">
              VS
            </div>
            <div>
              <h1 className="font-title text-base font-bold tracking-wide">VotoSeguro v2.0</h1>
              <p className="text-[11px] text-stone-300 font-sans">Verificador Universal de Comprobantes Criptográficos</p>
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

      {/* Contenido principal */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-seal-emerald text-xs font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>Verificación de Sufragio con Secreto Absoluto</span>
          </div>
          <h2 className="font-title text-2xl md:text-3xl font-bold text-civic-navy-900">
            Verificación Pública de Comprobante Electoral (S2-03)
          </h2>
          <p className="text-xs md:text-sm text-stone-600 max-w-2xl mx-auto">
            Introduce el código SHA-256 de tu comprobante digital o físico. El sistema comprobará matemáticamente
            su incorporación en la cadena de votos de la urna sin revelar jamás por quién votaste.
          </p>
        </div>

        {/* Buscador de comprobante */}
        <div className="bg-white border border-stone-300 rounded-2xl p-6 shadow-electoral space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleVerify();
            }}
            className="space-y-3"
          >
            <label className="block text-xs font-mono font-bold uppercase text-stone-600">
              Código Hash del Comprobante (SHA-256)
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={receiptInput}
                onChange={(e) => setReceiptInput(e.target.value)}
                placeholder="Ej. a8f5c3b1e7... (64 caracteres hexadecimales)"
                className="flex-1 px-4 py-2.5 border border-stone-300 rounded-xl font-mono text-xs focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
              />
              <button
                type="submit"
                disabled={loading || !receiptInput.trim()}
                className="px-6 py-2.5 bg-civic-navy-900 text-white rounded-xl text-xs font-bold hover:bg-civic-navy-800 flex items-center justify-center space-x-2 transition-colors disabled:opacity-50 shrink-0"
              >
                <Search className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                <span>{loading ? 'Verificando en Urna...' : 'Verificar Papeleta'}</span>
              </button>
            </div>
          </form>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-3">
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Comprobante No Válido o No Encontrado</p>
                <p className="mt-0.5">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Tarjeta de resultado verificado */}
        {result && result.verified && (
          <div className="bg-white border border-stone-300 rounded-2xl p-6 md:p-8 shadow-electoral space-y-6 animate-fadeIn">
            {/* Encabezado del veredicto */}
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <CheckCircle2 className="w-8 h-8 text-seal-emerald shrink-0" />
                <div>
                  <h3 className="font-title text-base font-bold text-emerald-950">
                    COMPROBANTE VÁLIDO: VOTO REGISTRADO EN LA URNA
                  </h3>
                  <p className="text-xs text-emerald-800 mt-0.5">
                    {result.message}
                  </p>
                </div>
              </div>
              <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-mono font-bold">
                {result.status}
              </span>
            </div>

            {/* Metadatos de la elección */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                <span className="text-[10px] font-mono uppercase font-bold text-stone-500">Elección Oficial</span>
                <p className="font-title text-sm font-bold text-civic-navy-900">{result.election_name}</p>
                {result.organization_name && (
                  <p className="text-stone-600 flex items-center space-x-1">
                    <Building2 className="w-3.5 h-3.5 text-stone-400" />
                    <span>{result.organization_name}</span>
                  </p>
                )}
              </div>

              <div className="p-4 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                <span className="text-[10px] font-mono uppercase font-bold text-stone-500">Fecha y Hora de Emisión</span>
                <p className="font-mono text-xs font-bold text-stone-800 flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-seal-emerald" />
                  <span>{new Date(result.cast_at).toLocaleString()} (UTC)</span>
                </p>
                <p className="text-[11px] text-stone-500 font-mono truncate" title={result.receipt_hash}>
                  Hash: {result.receipt_hash.substring(0, 24)}...
                </p>
              </div>
            </div>

            {/* Prueba criptográfica en la cadena de votos (S2-03) */}
            {result.chain_proof && (
              <div className="border border-stone-200 rounded-xl p-5 space-y-4 bg-stone-50/50">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono font-bold uppercase text-civic-navy-900 flex items-center space-x-2">
                    <Binary className="w-4 h-4 text-seal-emerald" />
                    <span>Prueba Criptográfica en la Cadena de Votos</span>
                  </h4>
                  <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                    <Check className="w-3 h-3" />
                    <span>Cadena Íntegra</span>
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                  <div className="p-3 bg-white border border-stone-200 rounded-lg">
                    <span className="text-[10px] text-stone-500 uppercase block">Posición en Urna</span>
                    <span className="text-sm font-bold text-civic-navy-900">Bloque #{result.chain_proof.chain_index}</span>
                  </div>

                  <div className="p-3 bg-white border border-stone-200 rounded-lg">
                    <span className="text-[10px] text-stone-500 uppercase block">Hash Previo</span>
                    <span className="text-[11px] text-stone-700 truncate block" title={result.chain_proof.prev_hash}>
                      {result.chain_proof.prev_hash.substring(0, 16)}...
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-stone-200 rounded-lg">
                    <span className="text-[10px] text-stone-500 uppercase block">Hash del Bloque</span>
                    <span className="text-[11px] text-seal-emerald font-bold truncate block" title={result.chain_proof.vote_hash}>
                      {result.chain_proof.vote_hash.substring(0, 16)}...
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Aviso de Privacidad e Invariante de Secreto */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
              <div className="flex items-center space-x-2 font-bold">
                <Lock className="w-4 h-4 text-amber-700" />
                <span>Garantía Constitucional de Secreto del Voto (Invariantes #9 y #11)</span>
              </div>
              <p className="text-[11px] text-amber-800 leading-relaxed">
                Este comprobante matemático certifica la validez y depósito de tu papeleta en la urna sin vincular tu
                identidad ciudadana con el contenido de la selección efectuada. Ningún administrador, observador ni
                proceso automatizado puede conocer tu sentido de voto.
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Pie institucional */}
      <footer className="bg-white border-t border-stone-200 py-4 text-center text-xs text-stone-500 font-mono">
        VotoSeguro v2.0 • Plataforma Cívica de Auditoría Criptográfica e Inmutabilidad de Sufragio
      </footer>
    </div>
  );
};
