import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Shield,
  Key,
  Lock,
  Unlock,
  Users,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Download,
  ArrowLeft,
  RefreshCw,
  Eye,
  FileText,
} from 'lucide-react';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { api } from '@/lib/api';

interface TrusteeInput {
  index: number;
  name: string;
  email: string;
}

interface TrusteeStatus {
  share_index: number;
  trustee_name: string;
  trustee_email: string;
  commitment_hash: string;
  submitted_for_tally: boolean;
  submitted_at: string | null;
}

interface CeremonyStatusData {
  election_id: string;
  election_status: string;
  key_ceremony_completed: boolean;
  threshold_k: number;
  total_n: number;
  key_ceremony_hash: string | null;
  tally_ceremony_hash: string | null;
  paillier_public_n: string | null;
  paillier_key_size: number;
  trustees: TrusteeStatus[];
}

interface GeneratedShareItem {
  trustee_index: number;
  trustee_name: string;
  trustee_email: string;
  share_formatted: string;
  commitment_hash: string;
}

export const CryptoCeremonyPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();

  // Estado de carga y datos
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [ceremonyStatus, setCeremonyStatus] = useState<CeremonyStatusData | null>(null);

  // Parámetros de Setup
  const [thresholdK, setThresholdK] = useState(3);
  const [totalN, setTotalN] = useState(5);
  const [keySizeBits, setKeySizeBits] = useState(2048);
  const [trustees, setTrustees] = useState<TrusteeInput[]>(Array.from({length: 5}, (_, i) => ({index: i+1, name: '', email: ''})));
  const [setupLoading, setSetupLoading] = useState(false);
  const [generatedShares, setGeneratedShares] = useState<GeneratedShareItem[]>([]);
  const [copiedShareIndex, setCopiedShareIndex] = useState<number | null>(null);

  // Parámetros de Unlock (Desbloqueo de Urna)
  const [unlockSharesText, setUnlockSharesText] = useState<string[]>(['', '', '']);
  const [unlockLoading, setUnlockLoading] = useState(false);
  const [unlockedResult, setUnlockedResult] = useState<any | null>(null);

  const fetchStatus = async () => {
    if (!electionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<CeremonyStatusData>(`/elections/${electionId}/shamir/status`);
      setCeremonyStatus(data);
      if (data.threshold_k) {
        setThresholdK(data.threshold_k);
        setTotalN(data.total_n);
        // Inicializar slots de unlock según K
        setUnlockSharesText(Array(data.threshold_k).fill(''));
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al cargar estado de la ceremonia criptográfica');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [electionId]);

  const handleUpdateTrustee = (index: number, field: 'name' | 'email', value: string) => {
    setTrustees((prev) =>
      prev.map((t, idx) => (idx === index ? { ...t, [field]: value } : t))
    );
  };

  const handleSetupCeremony = async () => {
    if (!electionId) return;
    if (trustees.slice(0, totalN).some(t => !t.name.trim() || !t.email.trim())) {
      setError('Indique el nombre y correo real de cada custodio.'); return;
    }
    setSetupLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const payload = {
        threshold_k: Number(thresholdK),
        total_n: Number(totalN),
        key_size: Number(keySizeBits),
        trustees: trustees.slice(0, totalN).map((t, i) => ({
          trustee_index: i + 1,
          trustee_name: t.name,
          trustee_email: t.email,
        })),
      };

      const data = await api.post<any>(`/elections/${electionId}/shamir/setup`, payload);
      setGeneratedShares(data.trustees.map((t: any) => ({ trustee_index: t.share_index, trustee_name: t.trustee_name, trustee_email: t.trustee_email, share_formatted: t.share_token, commitment_hash: t.commitment_hash })));
      setSuccessMsg(
        `¡Ceremonia de claves completada! Se generaron ${totalN} fragmentos Shamir con quórum k=${thresholdK}. La clave privada fue destruida de la memoria RAM.`
      );
      await fetchStatus();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al ejecutar la ceremonia de claves');
    } finally {
      setSetupLoading(false);
    }
  };

  const handleCopyShare = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedShareIndex(index);
    setTimeout(() => setCopiedShareIndex(null), 2500);
  };

  const handleUnlockTally = async () => {
    if (!electionId) return;
    const validShares = unlockSharesText.map((s) => s.trim()).filter((s) => s.length > 0);
    if (validShares.length < thresholdK) {
      setError(`Se requieren al menos ${thresholdK} fragmentos válidos de custodios para abrir la urna.`);
      return;
    }

    setUnlockLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const payload = {
        shares: validShares,
      };
      const data = await api.post<any>(`/elections/${electionId}/shamir/unlock`, payload);
      setUnlockedResult(data);
      setUnlockSharesText(Array(thresholdK).fill(''));
      setGeneratedShares([]);
      setSuccessMsg(
        `¡Apertura y escrutinio homomórfico exitoso! Se reconstruyó la clave con quórum y se descifraron los acumuladores oficiales (TALLIED).`
      );
      await fetchStatus();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al desbloquear el escrutinio con los fragmentos suministrados');
    } finally {
      setUnlockLoading(false);
    }
  };

  const isSetupDone = Boolean(ceremonyStatus?.key_ceremony_completed);
  const isTallied = ceremonyStatus?.election_status === 'TALLIED' || Boolean(ceremonyStatus?.tally_ceremony_hash);

  return (
    <InstitutionalShell>
      <div className="max-w-6xl mx-auto space-y-6 py-6 px-4">
        {/* Encabezado y Navegación */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-stone-200 pb-4">
          <div className="space-y-1">
            <Link
              to={`/workspace`}
              className="text-xs font-semibold text-stone-500 hover:text-stone-800 flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Volver al Espacio de Elecciones
            </Link>
            <h1 className="text-2xl font-bold font-serif text-civic-navy-950 flex items-center gap-2">
              <Key className="w-6 h-6 text-amber-500" />
              Ceremonia Criptográfica Paillier & Shamir ($k$ de $n$)
            </h1>
            <p className="text-xs text-stone-600">
              S3-01 & S3-02: Custodia multipartita de claves de descifrado y apertura homomórfica de urnas.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-stone-50 text-xs font-medium text-stone-700 flex items-center gap-1.5 shadow-sm transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Actualizar Estado
            </button>
            {isTallied && (
              <Link
                to={`/elections/${electionId}/results`}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white flex items-center gap-1.5 shadow-sm transition-colors"
              >
                <Eye className="w-3.5 h-3.5" />
                Ver Escrutinio Oficial
              </Link>
            )}
          </div>
        </div>

        {/* Alertas */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start gap-2.5 shadow-sm animate-in fade-in duration-150">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Error en la Ceremonia</p>
              <p>{error}</p>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-start gap-2.5 shadow-sm animate-in fade-in duration-150">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Operación Criptográfica Exitosa</p>
              <p>{successMsg}</p>
            </div>
          </div>
        )}

        {/* Resumen de Estado de la Ceremonia */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm space-y-1">
            <span className="text-[10px] font-semibold tracking-wider text-stone-500 uppercase">
              Estado de Elección
            </span>
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ${
                  ceremonyStatus?.election_status === 'TALLIED'
                    ? 'bg-emerald-100 text-emerald-800'
                    : ceremonyStatus?.election_status === 'VOTING_CLOSED'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-blue-100 text-blue-800'
                }`}
              >
                {ceremonyStatus?.election_status || 'CARGANDO'}
              </span>
            </div>
          </div>

          <div className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm space-y-1">
            <span className="text-[10px] font-semibold tracking-wider text-stone-500 uppercase">
              Ceremonia de Claves
            </span>
            <p className="text-sm font-bold text-stone-900 flex items-center gap-1.5">
              {isSetupDone ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  COMPLETADA
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  PENDIENTE DE SETUP
                </>
              )}
            </p>
          </div>

          <div className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm space-y-1">
            <span className="text-[10px] font-semibold tracking-wider text-stone-500 uppercase">
              Quórum Shamir ($k$ de $n$)
            </span>
            <p className="text-sm font-mono font-bold text-stone-900">
              {ceremonyStatus?.threshold_k || thresholdK} de {ceremonyStatus?.total_n || totalN} custodios
            </p>
          </div>

          <div className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm space-y-1">
            <span className="text-[10px] font-semibold tracking-wider text-stone-500 uppercase">
              Cifrado Homomórfico
            </span>
            <p className="text-xs font-mono font-bold text-stone-900">
              Paillier ({ceremonyStatus?.paillier_key_size || keySizeBits} bits)
            </p>
          </div>
        </div>

        {/* Sellos de Ceremonia */}
        {isSetupDone && (
          <div className="bg-stone-900 text-stone-200 rounded-xl p-4 border border-stone-800 shadow-md space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5 font-mono">
                <Shield className="w-4 h-4" />
                SELLOS CRIPTOGRÁFICOS DE CUSTODIA MULTIPARTITA
              </span>
              <span className="text-[10px] font-mono text-stone-400">Invariantes #13 & #20</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div className="bg-stone-950/80 p-2.5 rounded-lg border border-stone-800">
                <span className="text-stone-500 block text-[10px]">key_ceremony_hash (SHA-256):</span>
                <span className="text-emerald-400 break-all select-all font-semibold">
                  {ceremonyStatus?.key_ceremony_hash || 'N/D'}
                </span>
              </div>
              <div className="bg-stone-950/80 p-2.5 rounded-lg border border-stone-800">
                <span className="text-stone-500 block text-[10px]">tally_ceremony_hash (SHA-256):</span>
                <span className="text-emerald-400 break-all select-all font-semibold">
                  {ceremonyStatus?.tally_ceremony_hash || 'Pendiente de apertura de urna'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* FASE 1: SETUP DE CUSTODIOS Y GENERACIÓN DE LLAVES */}
        <div className="bg-white border border-stone-200 rounded-xl p-6 shadow-sm space-y-6">
          <div className="border-b border-stone-100 pb-3 flex items-center justify-between">
            <div className="space-y-0.5">
              <h2 className="text-lg font-bold font-serif text-stone-900 flex items-center gap-2">
                <Users className="w-5 h-5 text-civic-navy-900" />
                Fase 1: Configuración de Custodios y Reparto de Secreto ($k$ de $n$)
              </h2>
              <p className="text-xs text-stone-500">
                Define a las autoridades electorales custodias del secreto homomórfico.
              </p>
            </div>
            {isSetupDone && (
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Llaves Generadas
              </span>
            )}
          </div>

          {!isSetupDone ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-stone-700 mb-1">
                    Quórum Requerido ($k$)
                  </label>
                  <input
                    type="number"
                    min={2}
                    max={totalN}
                    value={thresholdK}
                    onChange={(e) => setThresholdK(Math.max(2, Math.min(totalN, Number(e.target.value))))}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-civic-navy-900 focus:outline-none"
                  />
                  <span className="text-[10px] text-stone-400">Mínimo de autoridades para descifrar</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-stone-700 mb-1">
                    Total Custodios ($n$)
                  </label>
                  <input
                    type="number"
                    min={thresholdK}
                    max={10}
                    value={totalN}
                    onChange={(e) => {
                      const n = Math.max(thresholdK, Number(e.target.value));
                      setTotalN(n);
                      // Expandir lista de custodios si es necesario
                      if (n > trustees.length) {
                        const next = [...trustees];
                        for (let i = trustees.length; i < n; i++) {
                          next.push({
                            index: i + 1,
                            name: '',
                            email: '',
                          });
                        }
                        setTrustees(next);
                      }
                    }}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-civic-navy-900 focus:outline-none"
                  />
                  <span className="text-[10px] text-stone-400">Total de fragmentos a emitir</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-stone-700 mb-1">
                    Tamaño Clave Paillier
                  </label>
                  <select
                    value={keySizeBits}
                    onChange={(e) => setKeySizeBits(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono bg-white focus:ring-2 focus:ring-civic-navy-900 focus:outline-none"
                  >
                    
                    <option value={2048}>2048 bits</option>
                  </select>
                  <span className="text-[10px] text-stone-400">Módulo $n = p \cdot q$ en urna</span>
                </div>
              </div>

              {/* Lista de Custodios */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-stone-600">
                  Custodios de la Corte Electoral ({totalN} Autoridades)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {trustees.slice(0, totalN).map((t, idx) => (
                    <div
                      key={idx}
                      className="p-3 border border-stone-200 rounded-lg bg-stone-50/70 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between font-semibold text-stone-700">
                        <span>Custodio #{idx + 1}</span>
                        <span className="text-[10px] font-mono text-stone-400">Share index: {idx + 1}</span>
                      </div>
                      <input
                        type="text"
                        value={t.name}
                        onChange={(e) => handleUpdateTrustee(idx, 'name', e.target.value)}
                        placeholder="Nombre de la Autoridad"
                        className="w-full px-2.5 py-1.5 border border-stone-300 rounded bg-white text-xs font-medium"
                      />
                      <input
                        type="email"
                        value={t.email}
                        onChange={(e) => handleUpdateTrustee(idx, 'email', e.target.value)}
                        placeholder="correo@institucion.org"
                        className="w-full px-2.5 py-1.5 border border-stone-300 rounded bg-white text-xs font-mono"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-3">
                <button
                  onClick={handleSetupCeremony}
                  disabled={setupLoading}
                  className="w-full py-2.5 px-4 rounded-xl bg-civic-navy-950 hover:bg-civic-navy-900 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-sm transition-all"
                >
                  <Key className={`w-4 h-4 ${setupLoading ? 'animate-spin' : ''}`} />
                  {setupLoading
                    ? 'Generando Claves Paillier y Fragmentos Shamir...'
                    : `Generar Par de Claves y Repartir (${thresholdK} de ${totalN})`}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3.5 bg-emerald-50/60 border border-emerald-200 rounded-lg text-xs text-emerald-950 flex items-center justify-between">
                <span>
                  La ceremonia de generación de claves fue efectuada con éxito. La clave privada Paillier fue dividida en{' '}
                  <strong>{ceremonyStatus?.total_n} fragmentos</strong> y purgada de la memoria RAM del servidor.
                </span>
              </div>

              {/* Listado de Custodios Registrados */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-stone-600">
                  Custodios Registrados en la Corte
                </h3>
                <div className="divide-y divide-stone-100 border border-stone-200 rounded-lg overflow-hidden">
                  {ceremonyStatus?.trustees.map((t) => (
                    <div key={t.share_index} className="p-3 flex items-center justify-between text-xs bg-white">
                      <div>
                        <p className="font-semibold text-stone-900">
                          #{t.share_index} — {t.trustee_name}
                        </p>
                        <p className="text-[11px] text-stone-500 font-mono">{t.trustee_email}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-stone-400 font-mono block">
                          Commitment: {t.commitment_hash.substring(0, 16)}...
                        </span>
                        <span
                          className={`inline-flex items-center text-[10px] font-bold ${
                            t.submitted_for_tally ? 'text-emerald-600' : 'text-stone-400'
                          }`}
                        >
                          {t.submitted_for_tally ? '✓ Suministrado en escrutinio' : 'Custodiado'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tabla de Fragmentos Recién Generados para Descarga/Copia */}
          {generatedShares.length > 0 && (
            <div className="mt-6 p-4 bg-amber-50/70 border border-amber-200 rounded-xl space-y-3">
              <button type="button" onClick={() => setGeneratedShares([])}>Ocultar fragmentos entregados</button>
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-amber-900 flex items-center gap-1.5 uppercase tracking-wide">
                  <Key className="w-4 h-4 text-amber-700" />
                  Fragmentos de Clave Emitidos (Copiar y Entregar a los Vocales)
                </h4>
                <span className="text-[10px] font-semibold text-amber-800">
                  ⚠️ Estos fragmentos solo se muestran una vez
                </span>
              </div>

              <div className="space-y-2">
                {generatedShares.map((s) => (
                  <div
                    key={s.trustee_index}
                    className="p-3 bg-white border border-amber-200 rounded-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-2 text-xs"
                  >
                    <div className="space-y-0.5">
                      <p className="font-semibold text-stone-800">
                        Custodio #{s.trustee_index}: {s.trustee_name} ({s.trustee_email})
                      </p>
                      <p className="font-mono text-[11px] text-stone-500 break-all select-all">
                        {s.share_formatted}
                      </p>
                    </div>
                    <button
                      onClick={() => handleCopyShare(s.share_formatted, s.trustee_index)}
                      className="px-2.5 py-1 rounded bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-medium flex items-center gap-1 transition-colors flex-shrink-0"
                    >
                      {copiedShareIndex === s.trustee_index ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" /> Copiado
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" /> Copiar Fragmento
                        </>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* FASE 2: DESBLOQUEO DE URNA Y ESCRUTINIO HOMOMÓRFICO */}
        <div className="bg-white border border-stone-200 rounded-xl p-6 shadow-sm space-y-6">
          <div className="border-b border-stone-100 pb-3 flex items-center justify-between">
            <div className="space-y-0.5">
              <h2 className="text-lg font-bold font-serif text-stone-900 flex items-center gap-2">
                <Unlock className="w-5 h-5 text-emerald-700" />
                Fase 2: Desbloqueo y Escrutinio por Quórum ($k$ de $n$)
              </h2>
              <p className="text-xs text-stone-500">
                Al cerrarse la votación (VOTING_CLOSED), se requiere que al menos {thresholdK} custodios suministren sus
                fragmentos para reconstruir la clave en RAM y descifrar los acumuladores oficiales.
              </p>
            </div>
            {isTallied && (
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Escrutinio Descifrado (TALLIED)
              </span>
            )}
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-stone-700">
                Ingrese al menos <strong>{thresholdK} fragmentos válidos</strong> de custodios:
              </p>

            </div>

            <div className="space-y-3">
              {unlockSharesText.map((val, idx) => (
                <div key={idx} className="space-y-1">
                  <label className="text-[11px] font-semibold text-stone-600 block">
                    Fragmento #{idx + 1} de Custodio
                  </label>
                  <input
                    type="text"
                    value={val}
                    onChange={(e) => {
                      const copy = [...unlockSharesText];
                      copy[idx] = e.target.value;
                      setUnlockSharesText(copy);
                    }}
                    placeholder="SHAMIR-SHARE-v1-..."
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-xs font-mono text-stone-800 focus:ring-2 focus:ring-emerald-600 focus:outline-none"
                  />
                </div>
              ))}
            </div>

            <div className="pt-2">
              <button
                onClick={handleUnlockTally}
                disabled={unlockLoading || isTallied}
                className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-stone-300 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-sm transition-all"
              >
                <Unlock className={`w-4 h-4 ${unlockLoading ? 'animate-spin' : ''}`} />
                {unlockLoading
                  ? 'Reconstruyendo Clave con Lagrange y Descifrando Escrutinio...'
                  : isTallied
                  ? 'Escrutinio Homomórfico Ya Descifrado'
                  : `Verificar Fragmentos y Desbloquear Escrutinio (${thresholdK} de ${totalN})`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </InstitutionalShell>
  );
};
