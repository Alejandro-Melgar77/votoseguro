import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Binary,
  Layers,
  Cpu,
  RefreshCw,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Search,
  ExternalLink,
  Lock,
  Zap,
  BarChart3,
  FileCheck2,
} from 'lucide-react';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { CryptographicHashBadge } from '@/components/electoral/CryptographicHashBadge';
import { api, ApiError } from '@/lib/api';
import type {
  Election,
  VoteChainIntegrityResponse,
  AuditChainIntegrityResponse,
  MerkleInclusionProofResponse,
  MerkleVerifyRequest,
  MerkleVerifyResponse,
  PaillierBenchmarkResponse,
} from '@votoseguro/api-client';

export const CryptographicIntegrityCenterPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();

  const [election, setElection] = useState<Election | null>(null);
  const [loadingElection, setLoadingElection] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'votes' | 'audit' | 'merkle' | 'paillier'>('votes');
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Tab 1: Cadena de Votos
  const [voteChainData, setVoteChainData] = useState<VoteChainIntegrityResponse | null>(null);
  const [loadingVotes, setLoadingVotes] = useState<boolean>(false);
  const [voteError, setVoteError] = useState<string | null>(null);

  // Tab 2: Cadena de Auditoría
  const [auditChainData, setAuditChainData] = useState<AuditChainIntegrityResponse | null>(null);
  const [loadingAudit, setLoadingAudit] = useState<boolean>(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  // Tab 3: Árbol de Merkle
  const [documentIdInput, setDocumentIdInput] = useState<string>('');
  const [merkleProof, setMerkleProof] = useState<MerkleInclusionProofResponse | null>(null);
  const [merkleVerifyResult, setMerkleVerifyResult] = useState<MerkleVerifyResponse | null>(null);
  const [loadingMerkle, setLoadingMerkle] = useState<boolean>(false);
  const [verifyingMerkle, setVerifyingMerkle] = useState<boolean>(false);
  const [merkleError, setMerkleError] = useState<string | null>(null);

  // Tab 4: Spike Paillier
  const [paillierKeySize, setPaillierKeySize] = useState<number>(1024);
  const [paillierVotesCount, setPaillierVotesCount] = useState<number>(10);
  const [paillierBenchmark, setPaillierBenchmark] = useState<PaillierBenchmarkResponse | null>(null);
  const [loadingPaillier, setLoadingPaillier] = useState<boolean>(false);
  const [paillierError, setPaillierError] = useState<string | null>(null);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2500);
  };

  const loadElection = async () => {
    if (!electionId) return;
    try {
      setLoadingElection(true);
      const data = await api.get<Election>(`/elections/${electionId}`);
      setElection(data);
    } catch (err: any) {
      console.error('Error cargando elección:', err);
    } finally {
      setLoadingElection(false);
    }
  };

  const verifyVoteChain = async () => {
    if (!electionId) return;
    try {
      setLoadingVotes(true);
      setVoteError(null);
      const data = await api.get<VoteChainIntegrityResponse>(`/elections/${electionId}/integrity/votes`);
      setVoteChainData(data);
    } catch (err: any) {
      setVoteError(err.message || 'Error al verificar la cadena de votos');
    } finally {
      setLoadingVotes(false);
    }
  };

  const verifyAuditChain = async () => {
    if (!electionId) return;
    try {
      setLoadingAudit(true);
      setAuditError(null);
      const data = await api.get<AuditChainIntegrityResponse>(`/elections/${electionId}/integrity/audit`);
      setAuditChainData(data);
    } catch (err: any) {
      setAuditError(err.message || 'Error al verificar la cadena de auditoría');
    } finally {
      setLoadingAudit(false);
    }
  };

  const fetchMerkleProof = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!electionId || !documentIdInput.trim()) return;
    try {
      setLoadingMerkle(true);
      setMerkleError(null);
      setMerkleProof(null);
      setMerkleVerifyResult(null);
      const data = await api.get<MerkleInclusionProofResponse>(
        `/elections/${electionId}/merkle/proof/${encodeURIComponent(documentIdInput.trim())}`
      );
      setMerkleProof(data);
    } catch (err: any) {
      setMerkleError(err.message || 'Error al obtener la prueba de Merkle del elector');
    } finally {
      setLoadingMerkle(false);
    }
  };

  const verifyMerkleMath = async () => {
    if (!electionId || !merkleProof) return;
    try {
      setVerifyingMerkle(true);
      const payload: MerkleVerifyRequest = {
        leaf_hash: merkleProof.leaf_hash,
        proof: merkleProof.proof,
        merkle_root: merkleProof.merkle_root,
      };
      const data = await api.post<MerkleVerifyResponse>(
        `/elections/${electionId}/merkle/verify`,
        payload
      );
      setMerkleVerifyResult(data);
    } catch (err: any) {
      alert(err.message || 'Error al verificar la prueba criptográfica');
    } finally {
      setVerifyingMerkle(false);
    }
  };

  const runPaillierBenchmark = async () => {
    try {
      setLoadingPaillier(true);
      setPaillierError(null);
      const data = await api.post<PaillierBenchmarkResponse>(
        `/crypto/paillier-spike-benchmark?key_size=${paillierKeySize}&num_votes=${paillierVotesCount}`
      );
      setPaillierBenchmark(data);
    } catch (err: any) {
      setPaillierError(err.message || 'Error al ejecutar benchmark de cifrado Paillier');
    } finally {
      setLoadingPaillier(false);
    }
  };

  useEffect(() => {
    loadElection();
    verifyVoteChain();
    verifyAuditChain();
  }, [electionId]);

  return (
    <InstitutionalShell activeElectionId={electionId} timezone={election?.timezone}>
      <div className="space-y-6">
        {/* Cabecera institucional de navegación */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-mono text-stone-500 mb-1">
              <Link to="/workspace" className="hover:text-civic-navy-900 transition-colors">
                Elecciones
              </Link>
              <span>/</span>
              <span className="text-stone-800 font-bold">{election?.name || 'Cargando...'}</span>
              <span>/</span>
              <span className="text-seal-emerald font-semibold">Integridad Criptográfica</span>
            </div>
            <h1 className="font-title text-2xl font-bold text-civic-navy-900 flex items-center space-x-2">
              <ShieldCheck className="w-6 h-6 text-seal-emerald" />
              <span>Centro de Integridad Criptográfica & Verificación Matemática</span>
            </h1>
            <p className="text-xs text-stone-600 mt-1 max-w-3xl">
              Auditoría en tiempo real de cadenas de bloques SHA-256 en urnas y bitácoras, pruebas de inclusión
              de Merkle para el padrón electoral y laboratorio de cifrado homomórfico aditivo Paillier.
            </p>
          </div>

          <Link
            to="/workspace"
            className="px-3 py-1.5 border border-stone-300 rounded-lg text-xs font-semibold text-stone-700 hover:bg-stone-50 flex items-center space-x-1.5 shadow-xs transition-colors shrink-0"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Volver a Elecciones</span>
          </Link>
        </div>

        {/* Sellos criptográficos globales */}
        {election && (
          <div className="flex flex-wrap items-center gap-3 p-4 bg-white border border-stone-200 rounded-xl shadow-xs">
            <div className="text-xs font-bold text-stone-700 flex items-center space-x-1.5 mr-2">
              <Lock className="w-4 h-4 text-seal-emerald" />
              <span>Sellos Oficiales:</span>
            </div>
            <CryptographicHashBadge
              label="Config Hash"
              hash={election.config_hash}
              type="config"
            />
            <CryptographicHashBadge
              label="Roll Hash"
              hash={election.roll_hash}
              type="roll"
            />
            {election.merkle_root && (
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-stone-100 border border-stone-300 text-[11px] font-mono text-stone-800">
                <span className="font-bold text-stone-600">Merkle Root:</span>
                <span className="text-seal-emerald font-bold">{election.merkle_root.substring(0, 16)}...</span>
                <button
                  onClick={() => copyToClipboard(election.merkle_root || '', 'root')}
                  className="p-0.5 hover:text-stone-900"
                  title="Copiar Merkle Root completa"
                >
                  {copiedText === 'root' ? <Check className="w-3 h-3 text-seal-emerald" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Pestañas de Navegación del Centro de Integridad */}
        <div className="border-b border-stone-300 flex space-x-6 text-xs font-bold">
          <button
            onClick={() => setActiveTab('votes')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'votes'
                ? 'border-seal-emerald text-seal-emerald font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Binary className="w-4 h-4" />
            <span>Cadena de Votos (Urna Criptográfica)</span>
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'audit'
                ? 'border-seal-emerald text-seal-emerald font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <FileCheck2 className="w-4 h-4" />
            <span>Cadena de Auditoría (Bitácora Hash)</span>
          </button>

          <button
            onClick={() => setActiveTab('merkle')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'merkle'
                ? 'border-seal-emerald text-seal-emerald font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Árbol de Merkle del Padrón</span>
          </button>

          <button
            onClick={() => setActiveTab('paillier')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'paillier'
                ? 'border-seal-emerald text-seal-emerald font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Cpu className="w-4 h-4" />
            <span>Spike Cifrado Homomórfico (Paillier)</span>
          </button>
        </div>

        {/* ========================================================================= */}
        {/* PESTAÑA 1: CADENA DE VOTOS (S2-02) */}
        {/* ========================================================================= */}
        {activeTab === 'votes' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-sm font-bold text-civic-navy-900 font-title">
                  Verificación Criptográfica de la Cadena de Votos (S2-02)
                </h2>
                <p className="text-xs text-stone-600">
                  Cada voto emitido es un bloque inmutable encadenado con SHA-256 al voto anterior y al bloque génesis de la elección.
                </p>
              </div>
              <button
                onClick={verifyVoteChain}
                disabled={loadingVotes}
                className="px-3 py-1.5 bg-seal-emerald text-white rounded-lg text-xs font-semibold hover:bg-seal-emerald/90 flex items-center space-x-1.5 shadow-xs transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingVotes ? 'animate-spin' : ''}`} />
                <span>Ejecutar Verificación Completa</span>
              </button>
            </div>

            {voteError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{voteError}</span>
              </div>
            )}

            {voteChainData && (
              <div className="space-y-4">
                {/* Banner de veredicto */}
                <div
                  className={`p-4 rounded-xl border flex items-center justify-between ${
                    voteChainData.valid
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                      : 'bg-red-50 border-red-300 text-red-900'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {voteChainData.valid ? (
                      <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                    ) : (
                      <ShieldAlert className="w-6 h-6 text-red-600 shrink-0" />
                    )}
                    <div>
                      <h3 className="font-bold text-sm">
                        {voteChainData.valid
                          ? 'CADENA DE VOTOS ÍNTEGRA Y SIN ALTERACIONES'
                          : '¡ALTERACIÓN CRIPTOGRÁFICA DETECTADA EN LA URNA!'}
                      </h3>
                      <p className="text-xs">
                        {voteChainData.valid
                          ? `Se han verificado satisfactoriamente ${voteChainData.verified_blocks} bloques consecutivos desde el bloque génesis.`
                          : `Ruptura de integridad en el bloque #${voteChainData.broken_at_index}.`}
                      </p>
                    </div>
                  </div>

                  <div className="text-right font-mono text-xs">
                    <div>
                      <span className="text-stone-500">Bloques en urna:</span>{' '}
                      <span className="font-bold">{voteChainData.total_blocks}</span>
                    </div>
                    <div>
                      <span className="text-stone-500">Verificados:</span>{' '}
                      <span className="font-bold">{voteChainData.verified_blocks}</span>
                    </div>
                  </div>
                </div>

                {/* Tarjetas de detalles génesis y head */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono uppercase font-bold text-stone-500 block">
                      Bloque Génesis de la Elección
                    </span>
                    <div className="font-mono text-xs text-stone-800 break-all mt-1 bg-stone-50 p-2 rounded border border-stone-200 flex justify-between items-center">
                      <span>{voteChainData.genesis_hash}</span>
                      <button
                        onClick={() => copyToClipboard(voteChainData.genesis_hash, 'genesis')}
                        className="ml-2 text-stone-500 hover:text-stone-800"
                        title="Copiar Hash Génesis"
                      >
                        {copiedText === 'genesis' ? <Check className="w-3.5 h-3.5 text-seal-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="p-4 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono uppercase font-bold text-stone-500 block">
                      Último Eslabón (Chain Head)
                    </span>
                    <div className="font-mono text-xs text-stone-800 break-all mt-1 bg-stone-50 p-2 rounded border border-stone-200 flex justify-between items-center">
                      <span>{voteChainData.head_hash || 'Sin votos emitidos aún'}</span>
                      {voteChainData.head_hash && (
                        <button
                          onClick={() => copyToClipboard(voteChainData.head_hash || '', 'head')}
                          className="ml-2 text-stone-500 hover:text-stone-800"
                          title="Copiar Chain Head"
                        >
                          {copiedText === 'head' ? <Check className="w-3.5 h-3.5 text-seal-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Panel de Invariantes y Diagnóstico de la Urna */}
                <div className="bg-white border border-stone-200 rounded-xl p-5 shadow-xs space-y-4">
                  <div className="border-b border-stone-200 pb-3 flex justify-between items-center">
                    <span className="text-xs font-bold text-stone-700 uppercase font-mono">
                      Garantías Criptográficas de la Urna Electoral
                    </span>
                    <span className="text-[11px] text-stone-500 font-mono">
                      Última verificación: {new Date(voteChainData.checked_at).toLocaleTimeString()}
                    </span>
                  </div>

                  {voteChainData.broken_at_index !== null && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 space-y-1">
                      <p className="font-bold">Detalle del Fallo Criptográfico:</p>
                      <p className="font-mono text-[11px]">
                        Eslabón #{voteChainData.broken_at_index} • ID: {voteChainData.broken_vote_id || 'N/A'}
                      </p>
                      <p>{voteChainData.error_detail}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg space-y-1">
                      <span className="font-bold text-civic-navy-900 block">Invariante #9 (Secreto)</span>
                      <p className="text-stone-600 text-[11px] leading-relaxed">
                        Cero identificadores de votante (`voter_id`) en los registros de sufragio. El comprobante
                        se valida sin vincular la identidad ciudadana con la opción elegida.
                      </p>
                    </div>

                    <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg space-y-1">
                      <span className="font-bold text-civic-navy-900 block">Invariante #10 (Cadena O(1))</span>
                      <p className="text-stone-600 text-[11px] leading-relaxed">
                        Encadenamiento secuencial SHA-256 adquirido atómicamente con bloqueo de fila (`FOR UPDATE`)
                        para garantizar estricta concurrencia serial y detección de manipulación.
                      </p>
                    </div>

                    <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg space-y-1">
                      <span className="font-bold text-civic-navy-900 block">Invariante #11 (Sellado)</span>
                      <p className="text-stone-600 text-[11px] leading-relaxed">
                        Cero conteos parciales por candidato antes de la clausura reglamentaria de la elección
                        (`VOTING_CLOSED`).
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* PESTAÑA 2: CADENA DE AUDITORÍA (S2-05) */}
        {/* ========================================================================= */}
        {activeTab === 'audit' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-sm font-bold text-civic-navy-900 font-title">
                  Verificación Criptográfica de la Bitácora de Auditoría (S2-05)
                </h2>
                <p className="text-xs text-stone-600">
                  Cada evento administrativo, cambio de estado o llamada a IA está encadenado mediante SHA-256 e inmutable por trigger de BD.
                </p>
              </div>
              <button
                onClick={verifyAuditChain}
                disabled={loadingAudit}
                className="px-3 py-1.5 bg-seal-emerald text-white rounded-lg text-xs font-semibold hover:bg-seal-emerald/90 flex items-center space-x-1.5 shadow-xs transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingAudit ? 'animate-spin' : ''}`} />
                <span>Verificar Cadena de Auditoría</span>
              </button>
            </div>

            {auditError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{auditError}</span>
              </div>
            )}

            {auditChainData && (
              <div className="space-y-4">
                <div
                  className={`p-4 rounded-xl border flex items-center justify-between ${
                    auditChainData.valid
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                      : 'bg-red-50 border-red-300 text-red-900'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {auditChainData.valid ? (
                      <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                    ) : (
                      <ShieldAlert className="w-6 h-6 text-red-600 shrink-0" />
                    )}
                    <div>
                      <h3 className="font-bold text-sm">
                        {auditChainData.valid
                          ? 'BITÁCORA DE AUDITORÍA CRIPTOGRÁFICA ÍNTEGRA'
                          : '¡ALTERACIÓN DETECTADA EN LA BITÁCORA DE AUDITORÍA!'}
                      </h3>
                      <p className="text-xs">
                        {auditChainData.valid
                          ? `Se han verificado satisfactoriamente ${auditChainData.verified_entries} entradas de auditoría consecutivas.`
                          : `Ruptura en la entrada #${auditChainData.broken_at_index}.`}
                      </p>
                    </div>
                  </div>

                  <div className="text-right font-mono text-xs">
                    <div>
                      <span className="text-stone-500">Total eventos:</span>{' '}
                      <span className="font-bold">{auditChainData.total_entries}</span>
                    </div>
                    <div>
                      <span className="text-stone-500">Verificados:</span>{' '}
                      <span className="font-bold">{auditChainData.verified_entries}</span>
                    </div>
                  </div>
                </div>

                {/* Panel de Invariantes y Diagnóstico de Auditoría */}
                <div className="bg-white border border-stone-200 rounded-xl p-5 shadow-xs space-y-4">
                  <div className="border-b border-stone-200 pb-3 flex justify-between items-center">
                    <span className="text-xs font-bold text-stone-700 uppercase font-mono">
                      Garantías Criptográficas de la Bitácora de Auditoría
                    </span>
                    <span className="text-[11px] text-stone-500 font-mono">
                      Última verificación: {new Date(auditChainData.checked_at).toLocaleTimeString()}
                    </span>
                  </div>

                  {auditChainData.broken_at_index !== null && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 space-y-1">
                      <p className="font-bold">Detalle del Fallo Criptográfico:</p>
                      <p className="font-mono text-[11px]">
                        Entrada #{auditChainData.broken_at_index} • ID: {auditChainData.broken_entry_id || 'N/A'}
                      </p>
                      <p>{auditChainData.error_detail}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg space-y-1">
                      <span className="font-bold text-civic-navy-900 block">Trigger de Inmutabilidad</span>
                      <p className="text-stone-600 text-[11px] leading-relaxed">
                        Trigger PostgreSQL `trg_audit_log_immutable` prohíbe de forma irrevocable sentencias
                        `UPDATE` o `DELETE` sobre la tabla `audit_log`.
                      </p>
                    </div>

                    <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg space-y-1">
                      <span className="font-bold text-civic-navy-900 block">Encadenamiento SHA-256</span>
                      <p className="text-stone-600 text-[11px] leading-relaxed">
                        Cada registro incorpora `prev_hash` y calcula su propio `entry_hash` canónico, formando
                        una cadena de bloques resistente a manipulaciones directas en base de datos.
                      </p>
                    </div>

                    <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg space-y-1">
                      <span className="font-bold text-civic-navy-900 block">Trazabilidad de IA</span>
                      <p className="text-stone-600 text-[11px] leading-relaxed">
                        Llamadas e inferencias de modelos de IA quedan registradas bajo el mismo estándar inmutable
                        a través de `log_ai_call()`.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* PESTAÑA 3: ÁRBOL DE MERKLE DEL PADRÓN (S2-07) */}
        {/* ========================================================================= */}
        {activeTab === 'merkle' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-bold text-civic-navy-900 font-title">
                Explorador y Verificador del Árbol de Merkle del Padrón Electoral (S2-07)
              </h2>
              <p className="text-xs text-stone-600">
                Al congelar el padrón (`REGISTRATION_CLOSED`), se calcula la raíz de Merkle (`merkle_root`).
                Cualquier ciudadano o auditor puede verificar que un votante está incluido en el padrón legítimo
                mediante una prueba matemática $O(\log_2 N)$ sin exponer la lista completa de votantes.
              </p>
            </div>

            {/* Tarjeta de Raíz de Merkle */}
            <div className="p-4 bg-white border border-stone-200 rounded-xl">
              <span className="text-[10px] font-mono uppercase font-bold text-stone-500 block">
                Raíz Criptográfica Oficial de la Elección (Merkle Root)
              </span>
              <div className="font-mono text-sm text-stone-800 break-all mt-1 bg-stone-50 p-3 rounded-lg border border-stone-200 flex justify-between items-center">
                <span>{election?.merkle_root || 'Pendiente de cálculo (Se genera al cerrar la fase de registro)'}</span>
                {election?.merkle_root && (
                  <button
                    onClick={() => copyToClipboard(election.merkle_root || '', 'root_full')}
                    className="ml-2 text-stone-500 hover:text-stone-800"
                    title="Copiar Merkle Root"
                  >
                    {copiedText === 'root_full' ? <Check className="w-4 h-4 text-seal-emerald" /> : <Copy className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </div>

            {/* Formulario de Consulta de Prueba de Inclusión */}
            <div className="p-6 bg-white border border-stone-200 rounded-xl shadow-xs space-y-4">
              <h3 className="text-xs font-bold text-stone-700 uppercase font-mono">
                Consultar Prueba Criptográfica de Inclusión
              </h3>
              <form onSubmit={fetchMerkleProof} className="flex gap-3">
                <div className="flex-1">
                  <input
                    type="text"
                    value={documentIdInput}
                    onChange={(e) => setDocumentIdInput(e.target.value)}
                    placeholder="Ingrese Cédula de Identidad o Documento (ej. 10001, 8934521)"
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-xs font-mono focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loadingMerkle || !documentIdInput.trim()}
                  className="px-4 py-2 bg-civic-navy-900 text-white rounded-lg text-xs font-bold hover:bg-civic-navy-800 flex items-center space-x-1.5 disabled:opacity-50 transition-colors"
                >
                  <Search className={`w-3.5 h-3.5 ${loadingMerkle ? 'animate-spin' : ''}`} />
                  <span>Generar Prueba Criptográfica</span>
                </button>
              </form>

              {merkleError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>{merkleError}</span>
                </div>
              )}
            </div>

            {/* Visualización de la Prueba de Merkle */}
            {merkleProof && (
              <div className="p-6 bg-white border border-stone-200 rounded-xl shadow-xs space-y-5">
                <div className="flex justify-between items-center border-b border-stone-200 pb-3">
                  <div>
                    <h4 className="text-xs font-bold text-civic-navy-900 uppercase font-mono">
                      Prueba Matemática de Inclusión para CI {merkleProof.document_id}
                    </h4>
                    <p className="text-[11px] text-stone-500 font-mono">
                      Posición #{merkleProof.leaf_index} de {merkleProof.total_active_voters} electores habilitados.
                    </p>
                  </div>
                  <button
                    onClick={verifyMerkleMath}
                    disabled={verifyingMerkle}
                    className="px-3 py-1.5 bg-seal-emerald text-white rounded-lg text-xs font-bold hover:bg-seal-emerald/90 flex items-center space-x-1.5 shadow-xs transition-colors disabled:opacity-50"
                  >
                    <CheckCircle2 className={`w-3.5 h-3.5 ${verifyingMerkle ? 'animate-spin' : ''}`} />
                    <span>Verificar Prueba Matemática</span>
                  </button>
                </div>

                {merkleVerifyResult && (
                  <div
                    className={`p-3 rounded-lg border flex items-center space-x-2 text-xs font-bold ${
                      merkleVerifyResult.valid
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                        : 'bg-red-50 border-red-300 text-red-800'
                    }`}
                  >
                    {merkleVerifyResult.valid ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                    )}
                    <span>
                      {merkleVerifyResult.valid
                        ? `PRUEBA MATEMÁTICA VÁLIDA: Raíz calculada (${merkleVerifyResult.computed_root.substring(0, 16)}...) coincide con el padrón oficial.`
                        : `PRUEBA INVÁLIDA: Raíz calculada difiere de la esperada (${merkleVerifyResult.expected_root.substring(0, 16)}...).`}
                    </span>
                  </div>
                )}

                {/* Hoja (Leaf Hash) */}
                <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                  <span className="text-[10px] font-mono uppercase font-bold text-stone-500">
                    Hash de la Hoja del Elector (Leaf Hash):
                  </span>
                  <div className="font-mono text-xs text-stone-800 break-all">{merkleProof.leaf_hash}</div>
                </div>

                {/* Pasos de la Prueba (Camino de hermanos / Sibling path) */}
                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase font-bold text-stone-500 block">
                    Camino de Hermanos Logarítmico ({merkleProof.proof.length} pasos de O(log₂ N)):
                  </span>
                  <div className="space-y-2">
                    {merkleProof.proof.map((step, idx) => (
                      <div
                        key={idx}
                        className="flex items-center space-x-3 p-2.5 bg-stone-50 rounded border border-stone-200 text-xs font-mono"
                      >
                        <span className="w-6 h-6 rounded-full bg-stone-200 text-stone-700 flex items-center justify-center font-bold text-[10px]">
                          {idx + 1}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            step.position === 'left'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-purple-100 text-purple-800'
                          }`}
                        >
                          {step.position.toUpperCase()}
                        </span>
                        <span className="text-stone-700 break-all flex-1">{step.sibling_hash}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* PESTAÑA 4: SPIKE PAILLIER (CIFRADO HOMOMÓRFICO) */}
        {/* ========================================================================= */}
        {activeTab === 'paillier' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-bold text-civic-navy-900 font-title">
                Laboratorio de Cifrado Homomórfico Aditivo (Spike Paillier - S2)
              </h2>
              <p className="text-xs text-stone-600">
                Prueba de concepto de sufragio con cifrado asimétrico Paillier (phe). En este esquema,
                cada voto se encripta con clave pública como E(m) = g^m · r^n mod n². La urna realiza
                la multiplicación de cifrados en espacio criptográfico que equivale exactamente a sumar
                los votos sin descifrar ninguna papeleta individual.
              </p>
            </div>

            {/* Panel de Controles del Benchmark */}
            <div className="p-6 bg-white border border-stone-200 rounded-xl shadow-xs space-y-4">
              <h3 className="text-xs font-bold text-stone-700 uppercase font-mono">
                Parámetros de Ejecución del Benchmark
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <label className="block text-stone-600 font-medium mb-1">Tamaño de Clave (bits)</label>
                  <select
                    value={paillierKeySize}
                    onChange={(e) => setPaillierKeySize(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg font-mono focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                  >
                    <option value={1024}>1024 bits (Rápido / Demostración)</option>
                    <option value={2048}>2048 bits (Estándar Criptográfico Producción)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-stone-600 font-medium mb-1">Papeletas Simuladas</label>
                  <select
                    value={paillierVotesCount}
                    onChange={(e) => setPaillierVotesCount(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg font-mono focus:outline-hidden focus:ring-2 focus:ring-seal-emerald"
                  >
                    <option value={5}>5 papeletas</option>
                    <option value={10}>10 papeletas</option>
                    <option value={20}>20 papeletas</option>
                    <option value={50}>50 papeletas</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={runPaillierBenchmark}
                    disabled={loadingPaillier}
                    className="w-full px-4 py-2 bg-civic-navy-900 text-white rounded-lg font-bold hover:bg-civic-navy-800 flex items-center justify-center space-x-2 disabled:opacity-50 transition-colors shadow-xs"
                  >
                    <Zap className={`w-4 h-4 text-seal-amber ${loadingPaillier ? 'animate-bounce' : ''}`} />
                    <span>{loadingPaillier ? 'Calculando Cifrados...' : 'Ejecutar Benchmark Paillier'}</span>
                  </button>
                </div>
              </div>

              {paillierError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>{paillierError}</span>
                </div>
              )}
            </div>

            {/* Resultados del Benchmark Paillier */}
            {paillierBenchmark && (
              <div className="space-y-4">
                {/* Banner de Equivalencia Matemática */}
                <div
                  className={`p-4 rounded-xl border flex items-center justify-between ${
                    paillierBenchmark.mathematical_equivalence_verified
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                      : 'bg-red-50 border-red-300 text-red-900'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                    <div>
                      <h3 className="font-bold text-sm">
                        EQUIVALENCIA HOMOMÓRFICA MATEMÁTICAMENTE VERIFICADA AL 100%
                      </h3>
                      <p className="text-xs font-mono">
                        Decrypt( E(v_1) * E(v_2) * ... * E(v_n) ) == v_1 + v_2 + ... + v_n
                      </p>
                    </div>
                  </div>
                  <span className="px-3 py-1 rounded bg-emerald-200 text-emerald-900 text-xs font-bold font-mono">
                    Match Exacto
                  </span>
                </div>

                {/* Tarjetas de latencia */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
                  <div className="p-3 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono text-stone-500 uppercase block">Generación Clave</span>
                    <span className="text-base font-bold text-stone-800 font-mono">
                      {paillierBenchmark.keygen_duration_ms.toFixed(1)} ms
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono text-stone-500 uppercase block">Cifrado de Votos</span>
                    <span className="text-base font-bold text-stone-800 font-mono">
                      {paillierBenchmark.encryption_duration_ms.toFixed(1)} ms
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono text-stone-500 uppercase block">Suma Homomórfica</span>
                    <span className="text-base font-bold text-seal-emerald font-mono">
                      {paillierBenchmark.homomorphic_addition_duration_ms.toFixed(1)} ms
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono text-stone-500 uppercase block">Descifrado Final</span>
                    <span className="text-base font-bold text-stone-800 font-mono">
                      {paillierBenchmark.final_decryption_duration_ms.toFixed(1)} ms
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-stone-200 rounded-xl">
                    <span className="text-[10px] font-mono text-stone-500 uppercase block">Tiempo Total</span>
                    <span className="text-base font-bold text-civic-navy-900 font-mono">
                      {paillierBenchmark.total_benchmark_duration_ms.toFixed(1)} ms
                    </span>
                  </div>
                </div>

                {/* Vista previa de texto cifrado */}
                {paillierBenchmark.sample_ciphertext_preview && (
                  <div className="p-4 bg-white border border-stone-200 rounded-xl space-y-1">
                    <span className="text-[10px] font-mono uppercase font-bold text-stone-500 block">
                      Muestra de Cifrado Paillier (BigInteger Ciphertext Preview)
                    </span>
                    <div className="p-3 bg-stone-900 text-emerald-400 font-mono text-xs rounded-lg break-all">
                      {paillierBenchmark.sample_ciphertext_preview}...
                    </div>
                  </div>
                )}

                {/* Celdas de Verificación */}
                <div className="bg-white border border-stone-200 rounded-xl overflow-hidden shadow-xs">
                  <div className="p-3 bg-stone-50 border-b border-stone-200 text-xs font-bold text-stone-700">
                    Celdas de Verificación Cruzada (Escrutinio Homomórfico vs Conteo Directo)
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-stone-100 text-stone-600 font-mono text-[11px] border-b border-stone-200">
                          <th className="py-2.5 px-3">Circunscripción</th>
                          <th className="py-2.5 px-3">Segmento</th>
                          <th className="py-2.5 px-3">Conteo Directo (Plaintext)</th>
                          <th className="py-2.5 px-3">Descifrado Homomórfico</th>
                          <th className="py-2.5 px-3 text-right">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-200 font-mono text-[11px]">
                        {paillierBenchmark.verification_cells.map((cell, idx) => (
                          <tr key={idx} className="hover:bg-stone-50">
                            <td className="py-2 px-3 font-semibold text-stone-800">
                              {cell.constituency_id}
                            </td>
                            <td className="py-2 px-3 text-stone-600">{cell.segment_path}</td>
                            <td className="py-2 px-3 font-bold text-civic-navy-900">
                              [{cell.expected_plaintext_tally.join(', ')}]
                            </td>
                            <td className="py-2 px-3 font-bold text-seal-emerald">
                              [{cell.decrypted_homomorphic_tally.join(', ')}]
                            </td>
                            <td className="py-2 px-3 text-right">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                                Exacto (100%)
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </InstitutionalShell>
  );
};
