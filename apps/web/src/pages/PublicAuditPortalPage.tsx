import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-store';
import {
  Shield,
  ShieldCheck,
  Lock,
  Layers,
  Clock,
  History,
  FileText,
  Search,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Eye,
  RefreshCw,
  ExternalLink,
  Users,
  Award,
} from 'lucide-react';
import { api } from '@/lib/api';
import { LanguageSwitcher } from '@/components/electoral/LanguageSwitcher';
import { useI18n } from '@/i18n';

interface PublicElectionSummary {
  election_id: string;
  name: string;
  organization_name: string;
  status: string;
  config_hash: string | null;
  roll_hash: string | null;
  merkle_root: string | null;
  voting_opens_at: string;
  voting_closes_at: string;
}

interface ScheduleChangeItem {
  id: string;
  field_name: string;
  old_value: string;
  new_value: string;
  reason: string;
  changed_at: string;
}

interface PublicAuditDossier {
  election_id: string;
  name: string;
  organization_name: string;
  status: string;
  timezone: string;
  k_anonymity: number;
  encryption_scheme: string;
  config_hash: string | null;
  roll_hash: string | null;
  merkle_root: string | null;
  key_ceremony_hash: string | null;
  tally_ceremony_hash: string | null;
  paillier_public_n: string | null;
  paillier_public_key: string | null;
  paillier_public_key_truncated: string | null;
  shamir_threshold_k: number;
  shamir_total_n: number;
  key_ceremony_status: string;
  voting_opens_at: string;
  voting_closes_at: string;
  schedule_changes: ScheduleChangeItem[];
  votes_integrity: {
    total_items: number;
    chain_valid: boolean;
    head_hash: string;
    genesis_hash: string | null;
  };
  audit_integrity: {
    total_items: number;
    chain_valid: boolean;
    head_hash: string;
  };
  total_registered_voters: number;
  total_votes_cast: number;
  turnout_percentage: number;
  results_published: boolean;
  results: Array<{
    constituency_id: string;
    constituency_label: string;
    ballots_aggregated: number;
    suppressed_by_k_anonymity: boolean;
    results: Record<string, any> | null;
  }> | null;
  results_notice: string | null;
}

export const PublicAuditPortalPage: React.FC = () => {
  const { isAuthenticated, homePath } = useAuth();
  const { electionId: routeElectionId } = useParams<{ electionId: string }>();
  const navigate = useNavigate();
  const { t } = useI18n();

  const [electionsList, setElectionsList] = useState<PublicElectionSummary[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState<string>(routeElectionId || '');
  const [dossier, setDossier] = useState<PublicAuditDossier | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // 1. Cargar lista de elecciones públicas
  useEffect(() => {
    const fetchElections = async () => {
      setListLoading(true);
      try {
        const list = await api.get<PublicElectionSummary[]>('/public/audit/elections');
        setElectionsList(list || []);
        if (list && list.length > 0 && !selectedElectionId) {
          setSelectedElectionId(list[0].election_id);
        }
      } catch (err: any) {
        console.error('Error al listar elecciones públicas:', err);
      } finally {
        setListLoading(false);
      }
    };
    fetchElections();
  }, []);

  // 2. Cargar expediente cuando cambia la elección seleccionada
  useEffect(() => {
    if (!selectedElectionId) return;

    const fetchDossier = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get<PublicAuditDossier>(`/public/audit/elections/${selectedElectionId}`);
        setDossier(data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Error al cargar expediente de auditoría');
      } finally {
        setLoading(false);
      }
    };
    fetchDossier();
  }, [selectedElectionId]);

  const handleSelectElection = (id: string) => {
    setSelectedElectionId(id);
    navigate(`/audit-portal/${id}`);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(label);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="min-h-screen bg-stone-100 flex flex-col font-sans text-stone-900">
      {/* Barra Superior de Auditoría */}
      <header className="bg-civic-navy-950 text-white border-b border-stone-800 px-4 py-3 sticky top-0 z-40 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2 text-white hover:opacity-90">
              <div className="w-8 h-8 rounded-lg bg-amber-500 text-stone-950 flex items-center justify-center font-bold font-serif text-sm">
                VS
              </div>
              <div>
                <span className="font-bold text-sm tracking-tight font-serif block">VotoSeguro v2</span>
                <span className="text-[10px] text-stone-400 font-mono tracking-wider uppercase block">
                  Portal Público de Auditoría (S3-03)
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-3">
            <LanguageSwitcher />

            <Link
              to="/verify-receipt"
              className="text-xs font-semibold text-stone-300 hover:text-white flex items-center gap-1.5 transition-colors border-l border-stone-800 pl-3"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Verificador de Comprobantes
            </Link>

            <Link
              to={isAuthenticated ? homePath : '/login'}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-stone-800 hover:bg-stone-700 text-stone-200 transition-colors"
            >
              {isAuthenticated ? 'Volver a mi panel' : 'Acceso Autoridades'}
            </Link>
          </div>
        </div>
      </header>

      {/* Selector de Elección y Banner Cívico */}
      <div className="bg-white border-b border-stone-200 py-6 px-4 shadow-sm">
        <div className="max-w-7xl mx-auto space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 font-mono">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                ACCESO PÚBLICO CIUDADANO (SIN INICIO DE SESIÓN)
              </div>
              <h1 className="text-2xl font-bold font-serif text-civic-navy-950">
                Expediente Público de Auditoría Integral
              </h1>
              <p className="text-xs text-stone-600">
                Inspección independiente de sellos matemáticos, cadena de bloques de urna, historial de cambios y resultados.
              </p>
            </div>

            {/* Dropdown de Elecciones */}
            <div className="w-full md:w-80 space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">
                Seleccionar Elección
              </label>
              <select
                value={selectedElectionId}
                onChange={(e) => handleSelectElection(e.target.value)}
                disabled={listLoading || electionsList.length === 0}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-xs font-medium bg-stone-50 focus:outline-none focus:ring-2 focus:ring-civic-navy-900"
              >
                {electionsList.map((e) => (
                  <option key={e.election_id} value={e.election_id}>
                    {e.name} ({e.status})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Contenido Principal */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {loading ? (
          <div className="p-16 text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-stone-400 animate-spin mx-auto" />
            <p className="text-xs font-semibold text-stone-600">Cargando expediente criptográfico de la elección...</p>
          </div>
        ) : dossier ? (
          <div className="space-y-6">
            {/* Ficha Resumen de la Elección */}
            <div className="bg-white border border-stone-200 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-100 pb-4">
                <div className="space-y-0.5">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-stone-400">
                    Institución Organizadora: {dossier.organization_name}
                  </span>
                  <h2 className="text-xl font-bold font-serif text-stone-900">{dossier.name}</h2>
                  <p className="text-xs text-stone-500 font-mono">
                    Zona Horaria: {dossier.timezone} • Umbral k-Anonimato: k={dossier.k_anonymity}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${
                      dossier.status === 'TALLIED'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : dossier.status === 'VOTING_OPEN'
                        ? 'bg-blue-100 text-blue-800 border border-blue-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {dossier.status}
                  </span>
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-stone-100 text-stone-700">
                    {dossier.encryption_scheme}
                  </span>
                </div>
              </div>

              {/* Métricas de Participación */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                <div className="p-4 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-stone-500 tracking-wider">
                    Padrón Habilitado
                  </span>
                  <p className="text-2xl font-bold font-mono text-stone-900">
                    {dossier.total_registered_voters.toLocaleString()}
                  </p>
                </div>

                <div className="p-4 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-stone-500 tracking-wider">
                    Votos Emitidos en Urna
                  </span>
                  <p className="text-2xl font-bold font-mono text-stone-900">
                    {dossier.total_votes_cast.toLocaleString()}
                  </p>
                </div>

                <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-1">
                  <span className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider">
                    Participación Ciudadana
                  </span>
                  <p className="text-2xl font-bold font-mono text-emerald-700">
                    {dossier.turnout_percentage}%
                  </p>
                </div>
              </div>
            </div>

            {/* Tarjetas de Verificación en Vivo de Cadenas e Integridad */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Cadena de Votos (Ledger) */}
              <div className="bg-white border border-stone-200 rounded-2xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5 text-emerald-600" />
                    <h3 className="font-bold text-sm font-serif text-stone-900">
                      Cadena de Hashes en Urna (Vote Ledger)
                    </h3>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      dossier.votes_integrity.chain_valid
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {dossier.votes_integrity.chain_valid ? 'CADENA VÁLIDA E INTACTA' : 'RUPTURA DE CADENA'}
                  </span>
                </div>

                <p className="text-xs text-stone-600">
                  Cada voto emitido incorpora un puntero criptográfico <code className="font-mono">prev_hash</code> y un{' '}
                  <code className="font-mono">vote_hash</code> verificable desde el bloque génesis (Invariante #19).
                </p>

                <div className="space-y-1.5 text-xs font-mono bg-stone-50 p-3 rounded-lg border border-stone-200">
                  <div className="flex justify-between">
                    <span className="text-stone-500">Total Votos Enlazados:</span>
                    <span className="font-bold text-stone-900">{dossier.votes_integrity.total_items}</span>
                  </div>
                  <div className="flex justify-between items-center gap-2">
                    <span className="text-stone-500">Último Hash (Head):</span>
                    <span className="text-emerald-700 font-semibold break-all text-[11px]">
                      {dossier.votes_integrity.head_hash.substring(0, 16)}...
                    </span>
                  </div>
                </div>
              </div>

              {/* Bitácora Inmutable (AuditLog) */}
              <div className="bg-white border border-stone-200 rounded-2xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-civic-navy-900" />
                    <h3 className="font-bold text-sm font-serif text-stone-900">
                      Cadena Inmutable de Auditoría (Audit Log)
                    </h3>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      dossier.audit_integrity.chain_valid
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {dossier.audit_integrity.chain_valid ? 'REGISTRO INMUTABLE VÁLIDO' : 'DISCREPANCIA DETECTADA'}
                  </span>
                </div>

                <p className="text-xs text-stone-600">
                  Todas las acciones del sistema y transiciones cronológicas se estampan con hashes encadenados (S2-05).
                </p>

                <div className="space-y-1.5 text-xs font-mono bg-stone-50 p-3 rounded-lg border border-stone-200">
                  <div className="flex justify-between">
                    <span className="text-stone-500">Total Entradas Auditadas:</span>
                    <span className="font-bold text-stone-900">{dossier.audit_integrity.total_items}</span>
                  </div>
                  <div className="flex justify-between items-center gap-2">
                    <span className="text-stone-500">Puntero de Bitácora:</span>
                    <span className="text-civic-navy-900 font-semibold break-all text-[11px]">
                      {dossier.audit_integrity.head_hash.substring(0, 16)}...
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Sellos Criptográficos Canónicos */}
            <div className="bg-white border border-stone-200 rounded-2xl p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-sm font-serif text-stone-900 uppercase tracking-wide flex items-center gap-2">
                <Award className="w-4 h-4 text-amber-500" />
                Sellos Criptográficos Canónicos del Proceso
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                {/* config_hash */}
                <div className="p-3 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                  <span className="text-[10px] text-stone-500 uppercase block">Config Hash (RFC 8785):</span>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-stone-900 font-bold break-all select-all">
                      {dossier.config_hash ? `${dossier.config_hash.substring(0, 18)}...` : 'N/D'}
                    </span>
                    {dossier.config_hash && (
                      <button
                        onClick={() => copyToClipboard(dossier.config_hash!, 'config')}
                        className="text-stone-400 hover:text-stone-800"
                      >
                        {copiedHash === 'config' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                </div>

                {/* roll_hash */}
                <div className="p-3 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                  <span className="text-[10px] text-stone-500 uppercase block">Roll Hash (Padrón Sellado):</span>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-stone-900 font-bold break-all select-all">
                      {dossier.roll_hash ? `${dossier.roll_hash.substring(0, 18)}...` : 'N/D'}
                    </span>
                    {dossier.roll_hash && (
                      <button
                        onClick={() => copyToClipboard(dossier.roll_hash!, 'roll')}
                        className="text-stone-400 hover:text-stone-800"
                      >
                        {copiedHash === 'roll' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                </div>

                {/* merkle_root */}
                <div className="p-3 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
                  <span className="text-[10px] text-stone-500 uppercase block">Merkle Root (Padrón):</span>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-stone-900 font-bold break-all select-all">
                      {dossier.merkle_root ? `${dossier.merkle_root.substring(0, 18)}...` : 'N/D'}
                    </span>
                    {dossier.merkle_root && (
                      <button
                        onClick={() => copyToClipboard(dossier.merkle_root!, 'merkle')}
                        className="text-stone-400 hover:text-stone-800"
                      >
                        {copiedHash === 'merkle' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Custodia Paillier y Shamir */}
              <div className="p-4 bg-stone-900 text-stone-300 rounded-xl font-mono text-xs space-y-2">
                <div className="flex items-center justify-between text-amber-400">
                  <span className="font-bold flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" /> Custodia Multipartita Shamir ({dossier.shamir_threshold_k} de {dossier.shamir_total_n} custodios)
                  </span>
                  <span className="text-[10px] text-stone-400">Estado: {dossier.key_ceremony_status}</span>
                </div>
                <div className="break-all text-[11px] text-stone-400">
                  Clave Pública Paillier (n):{' '}
                  <span className="text-emerald-400 font-bold">{dossier.paillier_public_key_truncated || 'N/D'}</span>
                </div>
              </div>
            </div>

            {/* Historial Completo de Cambios de Cronograma (schedule_change) */}
            <div className="bg-white border border-stone-200 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <h3 className="font-bold text-sm font-serif text-stone-900 uppercase tracking-wide flex items-center gap-2">
                    <History className="w-4 h-4 text-civic-navy-900" />
                    Historial Público de Modificaciones del Cronograma ({dossier.schedule_changes.length})
                  </h3>
                  <p className="text-xs text-stone-500">
                    Transparencia y trazabilidad legal de cada ajuste temporal con su motivo oficial declarado (RF-57).
                  </p>
                </div>
              </div>

              {dossier.schedule_changes.length > 0 ? (
                <div className="border border-stone-200 rounded-xl overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-stone-50 border-b border-stone-200 text-stone-600 font-semibold">
                      <tr>
                        <th className="p-3">Fecha y Hora</th>
                        <th className="p-3">Hito Modificado</th>
                        <th className="p-3">Valor Anterior</th>
                        <th className="p-3">Valor Nuevo</th>
                        <th className="p-3">Motivo Oficial Declarado</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {dossier.schedule_changes.map((c) => (
                        <tr key={c.id} className="hover:bg-stone-50/50">
                          <td className="p-3 font-mono text-stone-500 text-[11px] whitespace-nowrap">
                            {new Date(c.changed_at).toLocaleString()}
                          </td>
                          <td className="p-3 font-semibold text-stone-800">{c.field_name}</td>
                          <td className="p-3 font-mono text-stone-500 text-[11px]">{c.old_value}</td>
                          <td className="p-3 font-mono font-semibold text-emerald-700 text-[11px]">{c.new_value}</td>
                          <td className="p-3 text-stone-700 max-w-xs">{c.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6 bg-stone-50 rounded-xl text-center text-xs text-stone-500">
                  El cronograma electoral no registró ninguna modificación posterior a su publicación oficial.
                </div>
              )}
            </div>

            {/* Escrutinio Oficial o Hermetismo */}
            <div className="bg-white border border-stone-200 rounded-2xl p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-sm font-serif text-stone-900 uppercase tracking-wide flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-600" />
                Resultados y Escrutinio Oficial
              </h3>

              {dossier.results_published && dossier.results ? (
                <div className="space-y-4">
                  <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-950">
                    {dossier.results_notice}
                  </div>

                  <div className="divide-y divide-stone-200 border border-stone-200 rounded-xl overflow-hidden">
                    {dossier.results.map((r) => (
                      <div key={r.constituency_id} className="p-4 space-y-2 bg-white">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-xs text-stone-900">{r.constituency_label}</h4>
                          <span className="text-xs font-mono text-stone-500">
                            Total Sufragios: {r.ballots_aggregated}
                          </span>
                        </div>

                        {r.suppressed_by_k_anonymity ? (
                          <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                            Cifra suprimida por regla de k-anonimato (menos de {dossier.k_anonymity} votantes para evitar reidentificación).
                          </div>
                        ) : r.results ? (
                          <div className="bg-stone-50 p-3 rounded-lg font-mono text-xs space-y-1">
                            {Object.entries(r.results).map(([cand, votes]) => (
                              <div key={cand} className="flex justify-between">
                                <span className="text-stone-700">{cand}:</span>
                                <span className="font-bold text-stone-900">{String(votes)} votos</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-stone-400 italic">Cómputo en proceso de consolidación.</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-6 bg-stone-50 border border-stone-200 rounded-xl text-center space-y-2 text-xs text-stone-600">
                  <Lock className="w-6 h-6 text-stone-400 mx-auto" />
                  <p className="font-semibold text-stone-800">
                    Resultados Herméticos hasta el Cierre Oficial (Invariante #11)
                  </p>
                  <p>{dossier.results_notice}</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-16 text-center text-xs text-stone-500">
            No se encontró información pública para la elección seleccionada.
          </div>
        )}
      </main>

      {/* Footer Público */}
      <footer className="bg-white border-t border-stone-200 py-6 text-center text-xs text-stone-500">
        <p>VotoSeguro v2 — Plataforma Soberana de Votación Electrónica y Auditoría Criptográfica</p>
        <p className="text-[11px] text-stone-400 mt-1">
          Facultad Integral del Chaco / UAGRM • Ingeniería de Software I (INF 422 SB)
        </p>
      </footer>
    </div>
  );
};
