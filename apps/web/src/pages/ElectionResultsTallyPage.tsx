import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  BarChart3,
  Lock,
  ShieldCheck,
  AlertTriangle,
  Clock,
  ArrowLeft,
  CheckCircle2,
  RefreshCw,
  Users,
  Layers,
  Building2,
  FileText,
  Printer,
  ChevronRight,
  EyeOff,
  Percent,
  Check,
  Ban,
} from 'lucide-react';
import {
  Election,
  ElectionResultsResponse,
  ParticipationMetricsResponse,
  GroupResult,
  ContestResult,
  ContestBreakdownResult,
} from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { formatElectoralDateTime } from '@/lib/timezone';

export const ElectionResultsTallyPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();
  const { isAdminGeneral } = useAuth();

  const [election, setElection] = useState<Election | null>(null);
  const [results, setResults] = useState<ElectionResultsResponse | null>(null);
  const [participation, setParticipation] = useState<ParticipationMetricsResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSealed, setIsSealed] = useState(false);

  // Selector de Grupo y Cargo
  const [selectedGroupIdx, setSelectedGroupIdx] = useState(0);

  // Modal de Cierre de Votación (exclusivo ADMIN_GENERAL)
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeReason, setCloseReason] = useState('Fin de jornada electoral reglamentaria.');
  const [closing, setClosing] = useState(false);
  const [closeError, setCloseError] = useState<string | null>(null);

  const loadData = async () => {
    if (!electionId) return;
    try {
      setLoading(true);
      setError(null);

      // Cargar Elección
      const el = await api.get<Election>(`/elections/${electionId}`);
      setElection(el);

      // Si la elección NO está cerrada, los resultados están sellados (Invariante #11)
      if (el.status !== 'VOTING_CLOSED' && el.status !== 'TALLIED') {
        setIsSealed(true);
        // Cargar métricas de participación ciudadana en tiempo real
        const part = await api.get<ParticipationMetricsResponse>(
          `/elections/${electionId}/participation`
        );
        setParticipation(part);
        setResults(null);
      } else {
        setIsSealed(false);
        // Cargar resultados oficiales con k-anonimato
        const res = await api.get<ElectionResultsResponse>(
          `/elections/${electionId}/results`
        );
        setResults(res);

        // También cargar participación
        try {
          const part = await api.get<ParticipationMetricsResponse>(
            `/elections/${electionId}/participation`
          );
          setParticipation(part);
        } catch {
          // opcional si ya concluyó
        }
      }
    } catch (err: any) {
      if (err.status === 403) {
        setIsSealed(true);
        try {
          const part = await api.get<ParticipationMetricsResponse>(
            `/elections/${electionId}/participation`
          );
          setParticipation(part);
        } catch {}
      } else {
        setError(err.message || 'Error al cargar los datos del centro de cómputo.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [electionId]);

  const handleCloseVotingNow = async () => {
    if (!electionId) return;
    try {
      setClosing(true);
      setCloseError(null);
      await api.post(`/elections/${electionId}/voting/close-now`, {
        reason: closeReason.trim(),
      });
      setShowCloseModal(false);
      await loadData();
    } catch (err: any) {
      setCloseError(err.message || 'Error al clausurar las urnas de votación.');
    } finally {
      setClosing(false);
    }
  };

  const currentGroup: GroupResult | undefined =
    results?.groups && results.groups[selectedGroupIdx];

  return (
    <InstitutionalShell activeElectionId={electionId} timezone={election?.timezone}>
      <div className="space-y-6">
        {/* Barra Superior con Navegación y Acciones */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <Link
            to="/workspace"
            className="inline-flex items-center space-x-1.5 text-xs font-bold text-stone-600 hover:text-stone-900"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Volver a Mis Elecciones</span>
          </Link>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2 bg-white border border-stone-300 rounded-lg text-stone-700 hover:bg-stone-50 text-xs font-bold flex items-center space-x-1 shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Actualizar Cómputo</span>
            </button>

            {results && (
              <button
                onClick={() => window.print()}
                className="px-3 py-2 bg-stone-800 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-sm hover:bg-stone-700 transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Imprimir Acta Oficial</span>
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {/* ================================================================= */}
        {/* CASO 1: URNAS SELLADAS (INVARIANTE #11) */}
        {/* ================================================================= */}
        {!loading && isSealed && (
          <div className="space-y-6">
            <div className="bg-white border border-stone-300 rounded-xl p-8 text-center shadow-md space-y-4 max-w-2xl mx-auto">
              <div className="w-16 h-16 bg-stone-100 border border-stone-300 text-civic-navy-900 rounded-full flex items-center justify-center mx-auto shadow-inner">
                <Lock className="w-8 h-8 text-civic-navy-900" />
              </div>

              <div className="space-y-1">
                <div className="inline-flex items-center space-x-1 px-3 py-1 bg-amber-100 text-amber-900 rounded-full text-2xs font-bold font-mono">
                  <span>INVARIANTE #11 — RESULTADOS SELLADOS</span>
                </div>
                <h2 className="text-xl font-bold font-serif text-stone-900">
                  Urnas Electorales Clausuradas Criptográficamente
                </h2>
                <p className="text-xs text-stone-600 max-w-md mx-auto">
                  Por estricto protocolo de seguridad cívica, los resultados por candidato están bloqueados con <strong>403 Forbidden</strong> hasta el cierre oficial de la votación (<strong>VOTING_CLOSED</strong>), impidiendo cualquier conteo preliminar que pueda condicionar la voluntad popular.
                </p>
              </div>

              {/* Botón de Cierre para ADMIN_GENERAL */}
              {isAdminGeneral && election && election.status === 'VOTING_OPEN' && (
                <div className="pt-4 border-t border-stone-200">
                  <button
                    onClick={() => setShowCloseModal(true)}
                    className="px-5 py-2.5 bg-red-700 hover:bg-red-800 text-white rounded-lg text-xs font-bold shadow flex items-center space-x-2 mx-auto transition-colors"
                  >
                    <Ban className="w-4 h-4" />
                    <span>Clausurar Urnas y Proceder al Escrutinio Oficial</span>
                  </button>
                  <span className="text-2xs text-stone-400 block mt-1">
                    Acción administrativa auditada e irreversible.
                  </span>
                </div>
              )}
            </div>

            {/* Participación Ciudadana en Tiempo Real */}
            {participation && (
              <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm space-y-4 max-w-2xl mx-auto">
                <div className="flex items-center justify-between border-b border-stone-200 pb-3">
                  <div className="flex items-center space-x-2">
                    <Users className="w-4 h-4 text-civic-navy-900" />
                    <h3 className="text-sm font-bold text-stone-900">Participación Ciudadana en Tiempo Real</h3>
                  </div>
                  <span className="text-xs font-bold text-emerald-800 font-mono bg-emerald-100 px-2.5 py-0.5 rounded-full">
                    {participation.participation_rate_pct}% Participación
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-3 bg-stone-50 rounded-lg border border-stone-200">
                    <span className="text-2xs font-mono text-stone-500 uppercase block">Padrón Habilitado</span>
                    <span className="text-xl font-bold font-mono text-stone-900">
                      {participation.total_active_voters}
                    </span>
                  </div>
                  <div className="p-3 bg-stone-50 rounded-lg border border-stone-200">
                    <span className="text-2xs font-mono text-stone-500 uppercase block">Votos Registrados</span>
                    <span className="text-xl font-bold font-mono text-emerald-700">
                      {participation.total_voted}
                    </span>
                  </div>
                </div>

                {/* Barra de Progreso */}
                <div className="w-full bg-stone-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-emerald-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(participation.participation_rate_pct, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* CASO 2: RESULTADOS OFICIALES Y k-ANONIMATO */}
        {/* ================================================================= */}
        {!loading && !isSealed && results && (
          <div className="space-y-6">
            {/* Cabecera del Cómputo */}
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 bg-emerald-100 text-emerald-900 rounded-full text-2xs font-bold font-mono">
                    ESCRUTINIO OFICIAL FINALIZADO
                  </span>
                  <span className="px-2.5 py-1 bg-stone-100 text-stone-700 border border-stone-300 rounded-full text-2xs font-bold font-mono">
                    k-Anonimato: k={results.k_anonymity}
                  </span>
                </div>
                <h2 className="text-lg font-bold font-serif text-stone-900 mt-1">{results.election_name}</h2>
                <span className="text-xs text-stone-500">
                  Estado: <strong className="text-stone-800">{results.status}</strong>
                </span>
              </div>

              {participation && (
                <div className="flex items-center space-x-4 bg-stone-50 border border-stone-200 p-3 rounded-lg text-xs">
                  <div>
                    <span className="text-2xs text-stone-500 block">Participación Total</span>
                    <strong className="text-sm font-bold text-stone-900 font-mono">
                      {participation.total_voted} / {participation.total_active_voters}
                    </strong>
                  </div>
                  <div className="text-right">
                    <span className="text-2xs text-stone-500 block">Tasa de Votación</span>
                    <span className="text-sm font-bold text-emerald-700 font-mono">
                      {participation.participation_rate_pct}%
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Selector de Grupos de Votantes */}
            {results.groups.length > 1 && (
              <div className="border-b border-stone-200 flex space-x-4">
                {results.groups.map((grp, idx) => (
                  <button
                    key={grp.group_id}
                    onClick={() => setSelectedGroupIdx(idx)}
                    className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
                      selectedGroupIdx === idx
                        ? 'border-civic-navy-900 text-civic-navy-900'
                        : 'border-transparent text-stone-500 hover:text-stone-800'
                    }`}
                  >
                    {grp.group_name} ({grp.group_code})
                  </button>
                ))}
              </div>
            )}

            {/* Cargos del Grupo Actual */}
            {currentGroup && (
              <div className="space-y-8">
                {currentGroup.contests.map((contest) => (
                  <div
                    key={contest.contest_id}
                    className="bg-white border border-stone-300 rounded-xl shadow-sm overflow-hidden"
                  >
                    {/* Encabezado del Cargo */}
                    <div className="bg-stone-50 border-b border-stone-200 p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="text-base font-bold font-serif text-stone-900">
                            {contest.contest_name}
                          </h3>
                          <span className="px-2 py-0.5 bg-stone-200 text-stone-700 rounded text-2xs font-bold">
                            Nivel: {contest.scope_level_name}
                          </span>
                        </div>
                        {contest.description && (
                          <p className="text-xs text-stone-500 mt-0.5">{contest.description}</p>
                        )}
                      </div>
                    </div>

                    {/* Circunscripciones del Cargo */}
                    <div className="p-5 space-y-6">
                      {contest.constituencies.map((constituency) => (
                        <div key={constituency.constituency_id} className="space-y-4">
                          {/* Resumen Superior de Circunscripción */}
                          <div className="bg-stone-50 border border-stone-200 rounded-lg p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
                            <div>
                              <span className="text-stone-500 font-sans">Circunscripción Territorial:</span>
                              <strong className="block text-stone-900 text-sm font-semibold">
                                {constituency.node_name} ({constituency.node_path})
                              </strong>
                            </div>

                            <div className="flex items-center space-x-4">
                              <div className="text-right">
                                <span className="text-stone-500 block text-2xs">Total Sufragios</span>
                                <strong className="text-base font-bold text-stone-900 font-mono">
                                  {constituency.total_cast}
                                </strong>
                              </div>

                              <div className="text-right">
                                <span className="text-stone-500 block text-2xs">Blancos / Nulos</span>
                                <span className="text-xs font-mono text-stone-700">
                                  {constituency.blank_count} B / {constituency.null_count} N
                                </span>
                              </div>

                              <div>
                                {constituency.exact_match_verified ? (
                                  <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-100 text-emerald-900 rounded-full text-2xs font-bold font-mono">
                                    <Check className="w-3.5 h-3.5 text-emerald-700" />
                                    <span>Conciliación 100% Exacta</span>
                                  </span>
                                ) : (
                                  <span className="px-2.5 py-1 bg-red-100 text-red-900 rounded-full text-2xs font-bold">
                                    Discrepancia Matemática
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Tabla de Candidatos y Votación General */}
                          <div className="space-y-2">
                            <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wider">
                              Resultados Generales por Candidatura
                            </h4>

                            <div className="border border-stone-200 rounded-lg overflow-hidden divide-y divide-stone-100">
                              {constituency.candidates.map((cand, idx) => (
                                <div key={cand.candidate_id} className="p-3 bg-white flex items-center justify-between gap-4 text-xs">
                                  <div className="flex items-center space-x-3 w-1/3">
                                    <span className="w-5 h-5 rounded-full bg-stone-100 border border-stone-300 text-stone-700 font-mono text-2xs font-bold flex items-center justify-center flex-shrink-0">
                                      {cand.ballot_order}
                                    </span>
                                    <div className="min-w-0">
                                      <span className="font-bold text-stone-900 block truncate">
                                        {cand.full_name}
                                      </span>
                                      {cand.party_affiliation && (
                                        <span className="text-2xs text-stone-500 block truncate">
                                          {cand.party_affiliation}
                                        </span>
                                      )}
                                    </div>
                                  </div>

                                  {/* Barra de Porcentaje */}
                                  <div className="flex-1 max-w-xs">
                                    <div className="w-full bg-stone-100 rounded-full h-2 overflow-hidden">
                                      <div
                                        className="bg-civic-navy-900 h-2 rounded-full"
                                        style={{ width: `${cand.percentage}%` }}
                                      />
                                    </div>
                                  </div>

                                  <div className="w-24 text-right">
                                    <span className="font-bold font-mono text-stone-900 block">
                                      {cand.votes_count} votos
                                    </span>
                                    <span className="text-2xs font-mono text-stone-500">
                                      {cand.percentage}%
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* =================================================== */}
                          {/* DESGLOSES CONFIGURADOS Y k-ANONIMATO (INVARIANTE #12) */}
                          {/* =================================================== */}
                          {constituency.breakdowns && constituency.breakdowns.length > 0 && (
                            <div className="space-y-4 pt-3 border-t border-stone-200">
                              <h4 className="text-xs font-bold text-stone-800 flex items-center space-x-1.5">
                                <Layers className="w-3.5 h-3.5 text-civic-navy-900" />
                                <span>Desgloses Jerárquicos y Filtros con k-Anonimato (k={results.k_anonymity})</span>
                              </h4>

                              {constituency.breakdowns.map((bd) => (
                                <div key={bd.breakdown_id} className="bg-stone-50/50 border border-stone-200 rounded-lg p-4 space-y-3">
                                  <div className="flex justify-between items-center text-xs">
                                    <span className="font-bold text-stone-800">
                                      Desglose: {bd.label || bd.level_name || bd.filter_key}
                                    </span>
                                    <span className="text-2xs font-mono text-stone-500">
                                      Tipo: {bd.kind}
                                    </span>
                                  </div>

                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {bd.cells.map((cell) => (
                                      <div
                                        key={cell.cell_id}
                                        className={`p-3 rounded-lg border text-xs space-y-2 ${
                                          cell.redacted_by_k_anonymity
                                            ? 'bg-amber-50/60 border-amber-300 text-amber-900'
                                            : 'bg-white border-stone-200 text-stone-800'
                                        }`}
                                      >
                                        <div className="flex justify-between items-start">
                                          <div>
                                            <span className="font-bold block">{cell.cell_name}</span>
                                            {cell.cell_path && (
                                              <span className="text-2xs font-mono text-stone-400 block">
                                                {cell.cell_path}
                                              </span>
                                            )}
                                          </div>
                                          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-stone-100">
                                            {cell.total_votes} votos
                                          </span>
                                        </div>

                                        {/* Celda Redactada por k-anonimato */}
                                        {cell.redacted_by_k_anonymity ? (
                                          <div className="p-2 bg-amber-100/70 border border-amber-300 rounded text-2xs space-y-1">
                                            <div className="font-bold flex items-center space-x-1 text-amber-900">
                                              <EyeOff className="w-3.5 h-3.5 text-amber-700" />
                                              <span>Protegido por k-Anonimato (Invariante #12)</span>
                                            </div>
                                            <p className="text-amber-800">
                                              {cell.k_anonymity_message ||
                                                `< ${cell.k_threshold} votos. Conteo desagregado suprimido para garantizar el secreto del sufragio individual.`}
                                            </p>
                                          </div>
                                        ) : (
                                          /* Celda Normal no Redactada (>= k) */
                                          <div className="space-y-1 pt-1 border-t border-stone-100">
                                            {cell.candidates?.map((c) => (
                                              <div key={c.candidate_id} className="flex justify-between text-2xs">
                                                <span className="truncate max-w-[150px]">{c.full_name}:</span>
                                                <span className="font-mono font-semibold">
                                                  {c.votes_count} ({c.percentage}%)
                                                </span>
                                              </div>
                                            ))}
                                            {(cell.blank_count !== null || cell.null_count !== null) && (
                                              <div className="text-3xs text-stone-400 text-right pt-0.5">
                                                Blancos: {cell.blank_count} | Nulos: {cell.null_count}
                                              </div>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL DE CIERRE DE VOTACIÓN (CLANDESTINIDAD DE URNAS) */}
        {/* ================================================================= */}
        {showCloseModal && (
          <div className="fixed inset-0 bg-stone-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white border border-stone-300 rounded-xl max-w-md w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="bg-red-700 text-white p-4 flex items-center space-x-2">
                <Ban className="w-5 h-5" />
                <h3 className="text-sm font-bold font-serif">Clausura Definitiva de Urnas Electorales</h3>
              </div>

              <div className="p-6 space-y-4">
                <p className="text-xs text-stone-600">
                  Esta acción cerrará oficialmente el período de votación (<strong>VOTING_CLOSED</strong>) y permitirá el cómputo final de resultados y desgloses con k-anonimato.
                </p>

                {closeError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                    {closeError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-stone-700 mb-1">
                    Motivo o Justificación del Cierre <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    required
                    value={closeReason}
                    onChange={(e) => setCloseReason(e.target.value)}
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-red-600"
                  />
                </div>

                <div className="flex items-center justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    disabled={closing}
                    onClick={() => setShowCloseModal(false)}
                    className="px-4 py-2 border border-stone-300 rounded-lg text-xs font-bold text-stone-700 hover:bg-stone-100"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    disabled={closing}
                    onClick={handleCloseVotingNow}
                    className="px-4 py-2 bg-red-700 hover:bg-red-800 text-white rounded-lg text-xs font-bold shadow flex items-center space-x-1.5 disabled:opacity-50"
                  >
                    {closing ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Clausurando...</span>
                      </>
                    ) : (
                      <>
                        <Ban className="w-4 h-4" />
                        <span>Confirmar Clausura de Urnas</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </InstitutionalShell>
  );
};
