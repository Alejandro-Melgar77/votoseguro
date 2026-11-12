import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Vote,
  ShieldCheck,
  Lock,
  UserCheck,
  AlertTriangle,
  CheckCircle2,
  Download,
  Printer,
  Search,
  ArrowRight,
  Layers,
  Building2,
  FileText,
  Key,
  EyeOff,
  Copy,
  Check,
  RotateCcw,
} from 'lucide-react';
import {
  AutomaticBallotResponse,
  ContestBallotItem,
  CastReceiptResponse,
  ReceiptVerificationResponse,
  VoterSessionResponse,
} from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { formatElectoralDateTime } from '@/lib/timezone';
import { IdCardOcrScannerModal } from '@/components/electoral/IdCardOcrScannerModal';
import { VoiceAccessibleBallotController } from '@/components/electoral/VoiceAccessibleBallotController';
import { ElectoralFaqAssistantWidget } from '@/components/electoral/ElectoralFaqAssistantWidget';

export const VoterBallotBoothPage: React.FC = () => {
  // Estado del flujo: 'login' | 'ballot' | 'review' | 'receipt'
  const [step, setStep] = useState<'login' | 'ballot' | 'receipt'>('login');

  // Login
  const [documentId, setDocumentId] = useState('');
  const [credentialCode, setCredentialCode] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [showOcrModal, setShowOcrModal] = useState(false);
  const [activeContestIndex, setActiveContestIndex] = useState(0);

  // Sesión y Papeleta
  const [voterToken, setVoterToken] = useState<string | null>(null);
  const [ballotData, setBallotData] = useState<AutomaticBallotResponse | null>(null);
  const [ballotLoading, setBallotLoading] = useState(false);
  const [ballotError, setBallotError] = useState<string | null>(null);

  // Selecciones del Votante: contest_id -> { choice_type, candidate_id, display_label }
  const [selections, setSelections] = useState<
    Record<
      string,
      {
        choice_type: 'CANDIDATE' | 'BLANK' | 'NULL';
        candidate_id?: string | null;
        display_label: string;
      }
    >
  >({});

  // Modal de Confirmación
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [castingVote, setCastingVote] = useState(false);
  const [castError, setCastError] = useState<string | null>(null);

  // Recibo Criptográfico
  const [receipt, setReceipt] = useState<CastReceiptResponse | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  // Verificación Pública del Recibo
  const [verificationResult, setVerificationResult] = useState<ReceiptVerificationResponse | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  const handleVoterLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);

    if (!documentId.trim() || !credentialCode.trim()) {
      setLoginError('Ingrese su Documento de Identidad y su Credencial de Votación.');
      return;
    }

    try {
      setLoginLoading(true);
      const res = await api.post<VoterSessionResponse>('/voter/login', {
        document_id: documentId.trim(),
        credential_code: credentialCode.trim(),
      });

      setVoterToken(res.access_token);
      localStorage.setItem('votoseguro_voter_token', res.access_token);

      // Cargar Papeleta Automática con el token de votante
      await loadBallot(res.access_token);
      setStep('ballot');
    } catch (err: any) {
      setLoginError(err.message || 'Error de autenticación. Verifique su CI y código de credencial.');
    } finally {
      setLoginLoading(false);
    }
  };

  const loadBallot = async (token: string) => {
    try {
      setBallotLoading(true);
      setBallotError(null);
      const data = await api.get<AutomaticBallotResponse>('/ballot', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setBallotData(data);
    } catch (err: any) {
      setBallotError(err.message || 'No se pudo cargar su papeleta electoral.');
    } finally {
      setBallotLoading(false);
    }
  };

  const handleSelectCandidate = (
    contestId: string,
    candidateId: string,
    candidateName: string,
    party?: string | null
  ) => {
    setSelections((prev) => ({
      ...prev,
      [contestId]: {
        choice_type: 'CANDIDATE',
        candidate_id: candidateId,
        display_label: party ? `${candidateName} (${party})` : candidateName,
      },
    }));
  };

  const handleSelectBlank = (contestId: string) => {
    setSelections((prev) => ({
      ...prev,
      [contestId]: {
        choice_type: 'BLANK',
        candidate_id: null,
        display_label: 'Voto en Blanco',
      },
    }));
  };

  const handleSelectNull = (contestId: string) => {
    setSelections((prev) => ({
      ...prev,
      [contestId]: {
        choice_type: 'NULL',
        candidate_id: null,
        display_label: 'Voto Nulo',
      },
    }));
  };

  const allContestsSelected =
    ballotData &&
    ballotData.contests.length > 0 &&
    ballotData.contests.every((c) => selections[c.contest_id]);

  const handleConfirmAndCast = async () => {
    if (!voterToken || !ballotData || !allContestsSelected) return;

    try {
      setCastingVote(true);
      setCastError(null);

      const votesPayload = ballotData.contests.map((c) => {
        const sel = selections[c.contest_id];
        return {
          contest_id: c.contest_id,
          constituency_id: c.constituency_id,
          choice_type: sel.choice_type,
          candidate_id: sel.candidate_id || null,
        };
      });

      const res = await api.post<CastReceiptResponse>(
        '/ballot/cast',
        { votes: votesPayload },
        {
          headers: {
            Authorization: `Bearer ${voterToken}`,
          },
        }
      );

      setReceipt(res);
      setShowReviewModal(false);
      setStep('receipt');
      // Destruir token de votante tras emisión
      localStorage.removeItem('votoseguro_voter_token');
      setVoterToken(null);
    } catch (err: any) {
      setCastError(err.message || 'Error al emitir el sufragio en la urna digital.');
    } finally {
      setCastingVote(false);
    }
  };

  const handleCopyHash = () => {
    if (receipt) {
      navigator.clipboard.writeText(receipt.receipt_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2500);
    }
  };

  const handleVerifyReceiptOnLedger = async () => {
    if (!receipt) return;
    try {
      setVerifying(true);
      setVerificationError(null);
      const res = await api.get<ReceiptVerificationResponse>(
        `/receipts/${receipt.receipt_hash}`
      );
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationError(err.message || 'No se pudo verificar el recibo en la urna.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-100 flex flex-col justify-between font-sans text-stone-900">
      {/* Cabecera Cívica de la Cabina */}
      <header className="bg-civic-navy-900 text-stone-100 border-b border-stone-800 shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center font-bold text-white shadow-sm">
              <Vote className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold tracking-tight text-base font-serif">VotoSeguro v1.0</span>
              <span className="block text-2xs text-stone-400 font-mono">CABINA ELECTORAL SOBERANA (SUFRAGIO CIEGO)</span>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs text-stone-300">
            <EyeOff className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-2xs">Invariante #9: Voto Desvinculado</span>
          </div>
        </div>
      </header>

      {/* Contenido Dinámico según Paso */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8">
        {/* ================================================================= */}
        {/* PASO 1: LOGIN DE VOTANTE */}
        {/* ================================================================= */}
        {step === 'login' && (
          <div className="max-w-md mx-auto bg-white border border-stone-300 rounded-xl shadow-md overflow-hidden">
            <div className="bg-stone-50 border-b border-stone-200 p-6 text-center space-y-2">
              <div className="w-12 h-12 bg-civic-navy-100 text-civic-navy-900 rounded-full flex items-center justify-center mx-auto">
                <Key className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold font-serif text-stone-900">Acceso a Cabina Electoral</h2>
              <p className="text-xs text-stone-600">
                Ingrese su Documento de Identidad y su Credencial Personal de Votación de un solo uso.
              </p>
            </div>

            <form onSubmit={handleVoterLogin} className="p-6 space-y-4">
              {loginError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>{loginError}</div>
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-bold text-stone-700">
                    Documento de Identidad (CI / DNI)
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowOcrModal(true)}
                    className="text-xs text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 transition-colors"
                  >
                    <span>📷</span> Escanear OCR
                  </button>
                </div>
                <input
                  type="text"
                  required
                  value={documentId}
                  onChange={(e) => setDocumentId(e.target.value)}
                  placeholder="Ej. CI-8001001"
                  className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-civic-navy-900"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-stone-700 mb-1">
                  Credencial Personal de Votación
                </label>
                <input
                  type="text"
                  required
                  value={credentialCode}
                  onChange={(e) => setCredentialCode(e.target.value.toUpperCase())}
                  placeholder="VS-XXXX-XXXX-XXXX"
                  className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-civic-navy-900"
                />
                <span className="text-2xs text-stone-400 block mt-1">
                  Código confidencial de 16 caracteres emitido al abrirse la votación.
                </span>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loginLoading}
                  className="w-full py-2.5 px-4 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-lg text-sm font-bold shadow transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {loginLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Validando Credencial...</span>
                    </>
                  ) : (
                    <>
                      <span>Ingresar a Mi Papeleta</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-2xs text-amber-900 space-y-1">
                <div className="font-semibold flex items-center space-x-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
                  <span>Modo Demostración Académica</span>
                </div>
                <p>
                  Si está evaluando el sistema, el administrador puede consultar las credenciales de los votantes habilitados en la pestaña <strong>Credenciales Demo</strong> del panel de empadronamiento.
                </p>
              </div>
            </form>
          </div>
        )}

        {/* ================================================================= */}
        {/* PASO 2: PAPELETA ELECTORAL AUTOMÁTICA */}
        {/* ================================================================= */}
        {step === 'ballot' && ballotData && (
          <div className="space-y-6">
            {/* Banner de Identidad del Votante */}
            <div className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <span className="text-2xs font-mono text-stone-500 uppercase tracking-wider">VOTANTE IDENTIFICADO</span>
                <h3 className="text-sm font-bold text-stone-900">{ballotData.voter.full_name}</h3>
                <div className="text-xs text-stone-600 flex items-center space-x-3 mt-0.5">
                  <span>CI: <strong className="font-mono">{ballotData.voter.document_id}</strong></span>
                  <span>Grupo: <strong>{ballotData.voter.group_name}</strong></span>
                  <span>Nodo: <strong className="font-mono">{ballotData.voter.node_path}</strong></span>
                </div>
              </div>
              <div className="bg-stone-100 border border-stone-300 rounded-lg px-3 py-1.5 text-right">
                <span className="text-2xs font-bold text-stone-600 block">ELECCIÓN OFICIAL</span>
                <span className="text-xs font-bold text-stone-900 font-serif">{ballotData.election_name}</span>
              </div>
            </div>

            {/* Aviso de Rigor Criptográfico */}
            <div className="bg-stone-50 border-l-4 border-emerald-600 p-3 rounded-r-lg text-xs text-stone-700 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <EyeOff className="w-4 h-4 text-emerald-700 flex-shrink-0" />
                <span>
                  <strong>Secreto del Sufragio Garantizado:</strong> Sus votos se depositan en la urna sin vincular su identidad (Invariante #9).
                </span>
              </div>
              <span className="text-2xs font-mono text-stone-500">
                {Object.keys(selections).length} de {ballotData.contests.length} cargos completados
              </span>
            </div>

            {/* IA-L4: Barra de Accesibilidad por Voz Local */}
            {ballotData.contests.length > 0 && (
              <VoiceAccessibleBallotController
                activeContestName={ballotData.contests[activeContestIndex]?.contest_name || 'Cargo'}
                candidates={
                  ballotData.contests[activeContestIndex]?.candidates.map((c) => ({
                    id: c.id,
                    name: c.name,
                    party: c.party_or_front,
                  })) || []
                }
                selectedChoiceType={
                  selections[ballotData.contests[activeContestIndex]?.contest_id]?.choice_type || null
                }
                selectedCandidateId={
                  selections[ballotData.contests[activeContestIndex]?.contest_id]?.candidate_id || null
                }
                contestIndex={activeContestIndex}
                totalContests={ballotData.contests.length}
                onSelectCandidate={(candId) => {
                  const targetContest = ballotData.contests[activeContestIndex];
                  const cand = targetContest?.candidates.find((c) => c.id === candId);
                  if (targetContest && cand) {
                    handleSelectCandidate(
                      targetContest.contest_id,
                      cand.id,
                      cand.name,
                      cand.party_or_front
                    );
                  }
                }}
                onSelectBlank={() => {
                  const targetContest = ballotData.contests[activeContestIndex];
                  if (targetContest) handleSelectBlank(targetContest.contest_id);
                }}
                onSelectNull={() => {
                  const targetContest = ballotData.contests[activeContestIndex];
                  if (targetContest) handleSelectNull(targetContest.contest_id);
                }}
                onNextContest={() => {
                  if (activeContestIndex < ballotData.contests.length - 1) {
                    setActiveContestIndex(activeContestIndex + 1);
                  }
                }}
                onPrevContest={() => {
                  if (activeContestIndex > 0) {
                    setActiveContestIndex(activeContestIndex - 1);
                  }
                }}
                onPrepareCast={() => {
                  setShowReviewModal(true);
                }}
                onConfirmCast={() => {
                  if (allContestsSelected) {
                    handleConfirmAndCast();
                  } else {
                    setShowReviewModal(true);
                  }
                }}
              />
            )}

            {/* Lista de Cargos Electorales Resueltos */}
            <div className="space-y-6">
              {ballotData.contests.map((contest, idx) => {
                const selected = selections[contest.contest_id];
                return (
                  <div
                    key={contest.contest_id}
                    className="bg-white border border-stone-300 rounded-xl shadow-sm overflow-hidden"
                  >
                    {/* Encabezado del Cargo */}
                    <div className="bg-stone-50 border-b border-stone-200 p-4 flex justify-between items-center">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="w-5 h-5 rounded-full bg-civic-navy-900 text-white text-xs font-bold flex items-center justify-center font-mono">
                            {idx + 1}
                          </span>
                          <h4 className="text-sm font-bold text-stone-900 font-serif">{contest.contest_name}</h4>
                          <span className="px-2 py-0.5 bg-stone-200 text-stone-700 rounded text-2xs font-bold">
                            Nivel {contest.scope_level_depth}: {contest.scope_level_name}
                          </span>
                        </div>
                        {contest.description && (
                          <p className="text-xs text-stone-500 mt-1 pl-7">{contest.description}</p>
                        )}
                        <span className="text-2xs text-stone-400 pl-7 block">
                          Circunscripción: {contest.node_name}
                        </span>
                      </div>

                      <div>
                        {selected ? (
                          <span className="inline-flex items-center space-x-1 px-2 py-1 bg-emerald-100 text-emerald-900 rounded-full text-2xs font-bold">
                            <CheckCircle2 className="w-3 h-3 text-emerald-700" />
                            <span>Seleccionado</span>
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-amber-100 text-amber-900 rounded-full text-2xs font-bold">
                            Pendiente
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Candidatos en Disputa */}
                    <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {contest.candidates.map((cand) => {
                        const isChosen =
                          selected &&
                          selected.choice_type === 'CANDIDATE' &&
                          selected.candidate_id === cand.id;
                        return (
                          <button
                            type="button"
                            key={cand.id}
                            onClick={() =>
                              handleSelectCandidate(
                                contest.contest_id,
                                cand.id,
                                cand.name,
                                cand.party_or_front
                              )
                            }
                            className={`p-3 rounded-lg border text-left transition-all flex items-start space-x-3 ${
                              isChosen
                                ? 'border-civic-navy-900 bg-civic-navy-50/40 ring-2 ring-civic-navy-900 shadow-sm'
                                : 'border-stone-200 hover:border-stone-400 bg-white'
                            }`}
                          >
                            <div className="w-6 h-6 rounded-full bg-stone-100 border border-stone-300 flex items-center justify-center font-bold text-xs font-mono flex-shrink-0 text-stone-700 mt-0.5">
                              {cand.ballot_order}
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className="block text-xs font-bold text-stone-900 truncate">
                                {cand.name}
                              </span>
                              {cand.party_or_front && (
                                <span className="block text-2xs text-stone-500 truncate">
                                  {cand.party_or_front}
                                </span>
                              )}
                            </div>
                            {isChosen && (
                              <CheckCircle2 className="w-5 h-5 text-civic-navy-900 flex-shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* Opciones Especiales: Blanco y Nulo */}
                    {(contest.allow_blank || contest.allow_null) && (
                      <div className="border-t border-stone-100 p-3 bg-stone-50/50 flex flex-wrap gap-2 text-xs">
                        {contest.allow_blank && (
                          <button
                            type="button"
                            onClick={() => handleSelectBlank(contest.contest_id)}
                            className={`px-3 py-1.5 rounded-lg border font-bold text-2xs transition-colors ${
                              selected && selected.choice_type === 'BLANK'
                                ? 'bg-stone-800 text-white border-stone-800'
                                : 'bg-white text-stone-700 border-stone-300 hover:bg-stone-100'
                            }`}
                          >
                            Voto en Blanco
                          </button>
                        )}
                        {contest.allow_null && (
                          <button
                            type="button"
                            onClick={() => handleSelectNull(contest.contest_id)}
                            className={`px-3 py-1.5 rounded-lg border font-bold text-2xs transition-colors ${
                              selected && selected.choice_type === 'NULL'
                                ? 'bg-stone-800 text-white border-stone-800'
                                : 'bg-white text-stone-700 border-stone-300 hover:bg-stone-100'
                            }`}
                          >
                            Voto Nulo
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Barra de Emisión */}
            <div className="bg-white border border-stone-300 rounded-xl p-4 shadow flex flex-col sm:flex-row items-center justify-between gap-3 sticky bottom-4">
              <div>
                <span className="text-xs font-bold text-stone-900 block">
                  {allContestsSelected
                    ? '¡Papeleta Completa y Lista para Emitir!'
                    : `Complete su selección en todos los cargos (${Object.keys(selections).length}/${ballotData.contests.length})`}
                </span>
                <span className="text-2xs text-stone-500">
                  Una vez confirmado, el voto no podrá ser modificado ni cancelado.
                </span>
              </div>

              <button
                type="button"
                disabled={!allContestsSelected}
                onClick={() => setShowReviewModal(true)}
                className="w-full sm:w-auto px-6 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-sm font-bold shadow transition-colors flex items-center justify-center space-x-2 disabled:opacity-40"
              >
                <span>Revisar y Emitir Mi Voto</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL DE CONFIRMACIÓN Y EMISIÓN ATÓMICA */}
        {/* ================================================================= */}
        {showReviewModal && ballotData && (
          <div className="fixed inset-0 bg-stone-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white border border-stone-300 rounded-xl max-w-lg w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="bg-civic-navy-900 text-white p-4 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Vote className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-sm font-bold font-serif">Confirmación Definitiva de Sufragio</h3>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <p className="text-xs text-stone-600">
                  Revise detenidamente sus elecciones antes del depósito atómico en la urna criptográfica:
                </p>

                <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 space-y-2 text-xs">
                  {ballotData.contests.map((c) => {
                    const sel = selections[c.contest_id];
                    return (
                      <div key={c.contest_id} className="flex justify-between border-b border-stone-200 pb-1.5 last:border-0 last:pb-0">
                        <span className="text-stone-500 font-semibold">{c.contest_name}:</span>
                        <span className="font-bold text-stone-900">{sel?.display_label || 'Sin selección'}</span>
                      </div>
                    );
                  })}
                </div>

                {castError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>{castError}</div>
                  </div>
                )}

                <div className="bg-stone-100 p-3 rounded-lg text-2xs text-stone-600 space-y-1">
                  <div className="font-bold text-stone-800 flex items-center space-x-1">
                    <Lock className="w-3 h-3 text-stone-600" />
                    <span>Invariantes Criptográficas en Ejecución:</span>
                  </div>
                  <ul className="list-disc pl-4 space-y-0.5">
                    <li>La tabla de votos no guarda su identidad (Invariante #9).</li>
                    <li>Un nullifier ciego HMAC-SHA256 evita doble voto sin revelar su opción (Invariante #8).</li>
                    <li>La marca de tiempo se trunca al minuto para evitar ataques de correlación (Invariante #17).</li>
                  </ul>
                </div>

                <div className="flex items-center justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    disabled={castingVote}
                    onClick={() => setShowReviewModal(false)}
                    className="px-4 py-2 border border-stone-300 rounded-lg text-xs font-bold text-stone-700 hover:bg-stone-100"
                  >
                    Regresar a Editar
                  </button>
                  <button
                    type="button"
                    disabled={castingVote}
                    onClick={handleConfirmAndCast}
                    className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow flex items-center space-x-2 disabled:opacity-50"
                  >
                    {castingVote ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Depositando en Urna...</span>
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4" />
                        <span>Confirmar y Depositar Votos</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* PASO 3: RECIBO CRIPTOGRÁFICO Y VERIFICACIÓN */}
        {/* ================================================================= */}
        {step === 'receipt' && receipt && (
          <div className="max-w-xl mx-auto space-y-6">
            <div className="bg-white border border-emerald-300 rounded-xl shadow-lg overflow-hidden p-6 space-y-5">
              <div className="text-center space-y-2">
                <div className="w-14 h-14 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto shadow-sm">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <h2 className="text-xl font-bold font-serif text-stone-900">
                  ¡Sufragio Depositado Exitosamente!
                </h2>
                <p className="text-xs text-stone-600">
                  Sus votos han sido codificados y registrados en la urna digital de forma atómica e irreversible.
                </p>
              </div>

              {/* Tarjeta del Recibo Criptográfico */}
              <div className="bg-stone-50 border border-stone-300 rounded-xl p-5 space-y-3 font-mono text-xs">
                <div className="flex justify-between border-b border-stone-200 pb-2">
                  <span className="text-stone-500 font-sans">Elección:</span>
                  <span className="font-bold text-stone-900">{receipt.election_name}</span>
                </div>
                <div className="flex justify-between border-b border-stone-200 pb-2">
                  <span className="text-stone-500 font-sans">Cargos Sufragados:</span>
                  <span className="font-bold text-stone-900">{receipt.votes_count}</span>
                </div>
                <div className="flex justify-between border-b border-stone-200 pb-2">
                  <span className="text-stone-500 font-sans">Timestamp Truncado:</span>
                  <span className="text-stone-800">{formatElectoralDateTime(receipt.cast_at)}</span>
                </div>
                <div className="space-y-1 pt-1">
                  <span className="text-stone-500 font-sans block text-2xs">
                    Huella Digital Criptográfica del Recibo (SHA-256):
                  </span>
                  <div className="p-2.5 bg-stone-900 text-emerald-400 rounded-lg text-xs break-all font-mono select-all flex items-center justify-between gap-2">
                    <span>{receipt.receipt_hash}</span>
                    <button
                      type="button"
                      onClick={handleCopyHash}
                      title="Copiar huella digital"
                      className="text-stone-400 hover:text-white p-1 rounded transition-colors"
                    >
                      {copiedHash ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Acciones de Guardado */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="w-full sm:w-1/2 py-2 px-4 bg-stone-200 hover:bg-stone-300 text-stone-800 rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-colors"
                >
                  <Printer className="w-4 h-4" />
                  <span>Imprimir Recibo</span>
                </button>
                <button
                  type="button"
                  onClick={handleVerifyReceiptOnLedger}
                  disabled={verifying}
                  className="w-full sm:w-1/2 py-2 px-4 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-colors shadow"
                >
                  {verifying ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Auditando Urna...</span>
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      <span>Auditar Recibo en Urna</span>
                    </>
                  )}
                </button>
              </div>

              {/* Resultado de la Auditoría en Tiempo Real */}
              {verificationResult && (
                <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center space-x-2 font-bold text-emerald-900">
                    <ShieldCheck className="w-5 h-5 text-emerald-700" />
                    <span>Verificación Pública Exitosa</span>
                  </div>
                  <p className="text-emerald-800 font-mono text-2xs">
                    {verificationResult.message}
                  </p>
                  <div className="text-2xs text-emerald-900 space-y-0.5 font-mono">
                    <div>Urna: <strong>{verificationResult.election_name}</strong></div>
                    <div>Minuto Registrado: <strong>{verificationResult.cast_at_minute}</strong></div>
                    <div>Votos Conciliados en Papeleta: <strong>{verificationResult.total_votes_in_ballot}</strong></div>
                  </div>
                </div>
              )}

              {verificationError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                  {verificationError}
                </div>
              )}

              <div className="pt-2 text-center">
                <Link
                  to="/"
                  className="text-xs font-bold text-civic-navy-900 hover:underline"
                >
                  Salir de la Cabina Electoral
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Pie de Página */}
      <footer className="bg-white border-t border-stone-200 py-4 text-center text-xs text-stone-500">
        <p>VotoSeguro v2.0 — Soberanía Ciudadana y Transparencia Electoral Criptográfica</p>
      </footer>

      {/* Modal OCR de Cédula */}
      <IdCardOcrScannerModal
        isOpen={showOcrModal}
        onClose={() => setShowOcrModal(false)}
        onConfirm={(data) => {
          setDocumentId(data.ci);
        }}
      />

      {/* Asistente Electoral Oficial RAG (Se oculta en step === 'ballot' - Invariante 7.3) */}
      <ElectoralFaqAssistantWidget isVotingStep={step === 'ballot'} />
    </div>
  );
};
