import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Users,
  Upload,
  UserPlus,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Search,
  Filter,
  ArrowLeft,
  RefreshCw,
  FileSpreadsheet,
  Download,
  Trash2,
  Ban,
  Check,
  ChevronRight,
  Info,
  Layers,
  Building2,
  Calendar,
  Lock,
  Link2,
  Key,
  Copy,
  Send,
  ExternalLink,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  Election,
  Voter,
  VoterGroup,
  UnitNode,
  RegistrationSummaryResponse,
  ImportBatch,
  ImportIssue,
  VoterStatus,
  RegistrationLink,
  CredentialDispatchItem,
  CredentialsDispatchResponse,
  RollHashFreezeResponse,
} from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { DuplicateAdjudicationDrawer } from '@/components/electoral/DuplicateAdjudicationDrawer';
import { formatElectoralDateTime } from '@/lib/timezone';

export const VoterRollRegistrationPanelPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();
  const { isAdminGeneral } = useAuth();

  const [election, setElection] = useState<Election | null>(null);
  const [summary, setSummary] = useState<RegistrationSummaryResponse | null>(null);
  const [groups, setGroups] = useState<VoterGroup[]>([]);
  const [nodes, setNodes] = useState<UnitNode[]>([]);
  const [voters, setVoters] = useState<Voter[]>([]);
  const [batches, setBatches] = useState<ImportBatch[]>([]);
  const [pendingDuplicates, setPendingDuplicates] = useState<ImportIssue[]>([]);

  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filtros de tabla
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGroupId, setSelectedGroupId] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  // Pestañas activas: 'voters' | 'import' | 'duplicates' | 'breakdown' | 'links' | 'credentials' | 'pending-approval'
  const [activeTab, setActiveTab] = useState<
    'voters' | 'import' | 'duplicates' | 'breakdown' | 'links' | 'credentials' | 'pending-approval'
  >('voters');

  // Gestión de Solicitudes de Autoinscripción (S2-10)
  const [pendingVoters, setPendingVoters] = useState<Voter[]>([]);
  const [loadingPending, setLoadingPending] = useState(false);
  const [actionVoterId, setActionVoterId] = useState<string | null>(null);
  const [rejectModalVoter, setRejectModalVoter] = useState<Voter | null>(null);
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [rejectSubmitting, setRejectSubmitting] = useState<boolean>(false);

  // Gestión de Enlaces de Registro (S1-08)
  const [links, setLinks] = useState<RegistrationLink[]>([]);
  const [showCreateLinkModal, setShowCreateLinkModal] = useState(false);
  const [createLinkGroupId, setCreateLinkGroupId] = useState('');
  const [createLinkNodeId, setCreateLinkNodeId] = useState('');
  const [createLinkLabel, setCreateLinkLabel] = useState('');
  const [createLinkExpiresAt, setCreateLinkExpiresAt] = useState('');
  const [createLinkMaxUses, setCreateLinkMaxUses] = useState('');
  const [createLinkSubmitting, setCreateLinkSubmitting] = useState(false);
  const [createLinkError, setCreateLinkError] = useState<string | null>(null);
  const [copiedLinkId, setCopiedLinkId] = useState<string | null>(null);
  const [sendingInvitations, setSendingInvitations] = useState(false);
  const [invitationsFeedback, setInvitationsFeedback] = useState<string | null>(null);

  // Despacho de Credenciales Demo (S1-09)
  const [credentials, setCredentials] = useState<CredentialDispatchItem[]>([]);
  const [credentialsTotal, setCredentialsTotal] = useState(0);
  const [credentialsLoading, setCredentialsLoading] = useState(false);
  const [copiedCredId, setCopiedCredId] = useState<string | null>(null);
  const [freezingRoll, setFreezingRoll] = useState(false);
  const [openingVoting, setOpeningVoting] = useState(false);
  const [rollFreezeFeedback, setRollFreezeFeedback] = useState<string | null>(null);

  // Modal Alta Individual
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createDocId, setCreateDocId] = useState('');
  const [createFullName, setCreateFullName] = useState('');
  const [createEmail, setCreateEmail] = useState('');
  const [createPhone, setCreatePhone] = useState('');
  const [createGroupId, setCreateGroupId] = useState('');
  const [createNodeId, setCreateNodeId] = useState('');
  const [createAttrsText, setCreateAttrsText] = useState('{}');
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Modal Carga Masiva CSV
  const [showImportModal, setShowImportModal] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importSubmitting, setImportSubmitting] = useState(false);
  const [importResult, setImportResult] = useState<ImportBatch | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Modal Bloqueo de Votante
  const [voterToBlock, setVoterToBlock] = useState<Voter | null>(null);
  const [blockReason, setBlockReason] = useState('Retiro por inhabilitación administrativa');
  const [blockSubmitting, setBlockSubmitting] = useState(false);

  // Arbitraje de Duplicados (IA-L2a)
  const [selectedDuplicateIssue, setSelectedDuplicateIssue] = useState<ImportIssue | null>(null);

  // Inspector de Lote de Importación
  const [inspectedBatchId, setInspectedBatchId] = useState<string | null>(null);
  const [inspectedBatchIssues, setInspectedBatchIssues] = useState<ImportIssue[]>([]);
  const [loadingBatchIssues, setLoadingBatchIssues] = useState(false);

  const isRegistrationOpen = election?.status === 'REGISTRATION_OPEN';

  const loadBaseData = async () => {
    if (!electionId) return;
    try {
      setLoading(true);
      setError(null);
      const [electRes, summRes, groupsRes, batchesRes, dupsRes] = await Promise.all([
        api.get<Election>(`/elections/${electionId}`),
        api.get<RegistrationSummaryResponse>(`/elections/${electionId}/registration/summary`),
        api.get<VoterGroup[]>(`/elections/${electionId}/groups`),
        api.get<ImportBatch[]>(`/elections/${electionId}/voters/import-batches`),
        api.get<ImportIssue[]>(`/elections/${electionId}/voters/duplicates`),
      ]);
      setElection(electRes);
      setSummary(summRes);
      setGroups(groupsRes);
      setBatches(batchesRes);
      setPendingDuplicates(dupsRes);

      // Cargar nodos aplanados de todos los grupos para selector
      if (groupsRes.length > 0) {
        const allNodesPromises = groupsRes.map((g) =>
          api.get<UnitNode[]>(`/groups/${g.id}/nodes/tree`).catch(() => [] as UnitNode[])
        );
        const trees = await Promise.all(allNodesPromises);
        const flat: UnitNode[] = [];
        const walk = (items: UnitNode[]) => {
          for (const item of items) {
            flat.push(item);
            if (item.children && item.children.length > 0) {
              walk(item.children);
            }
          }
        };
        trees.forEach((tree) => walk(tree));
        setNodes(flat);
      }

      // Cargar solicitudes pendientes de autoinscripción (S2-10)
      loadPendingVoters();
    } catch (err: any) {
      setError(err.message || 'Error al cargar los datos del padrón electoral.');
    } finally {
      setLoading(false);
    }
  };

  const loadVotersList = async () => {
    if (!electionId) return;
    try {
      setTableLoading(true);
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      if (selectedGroupId) params.append('group_id', selectedGroupId);
      if (selectedStatus) params.append('status', selectedStatus);
      params.append('limit', '100');

      const url = `/elections/${electionId}/voters?${params.toString()}`;
      const data = await api.get<Voter[]>(url);
      setVoters(data);
    } catch (err: any) {
      console.error('Error al listar votantes:', err);
    } finally {
      setTableLoading(false);
    }
  };

  useEffect(() => {
    loadBaseData();
  }, [electionId]);

  useEffect(() => {
    loadVotersList();
  }, [electionId, selectedGroupId, selectedStatus]);

  const loadPendingVoters = async () => {
    if (!electionId) return;
    try {
      setLoadingPending(true);
      const data = await api.get<Voter[]>(`/elections/${electionId}/voters/pending-approval`);
      setPendingVoters(data);
    } catch (err: any) {
      console.error('Error al listar solicitudes pendientes:', err);
    } finally {
      setLoadingPending(false);
    }
  };

  const handleApproveVoter = async (voterId: string) => {
    try {
      setActionVoterId(voterId);
      await api.post(`/voters/${voterId}/approve`);
      await loadPendingVoters();
      const summ = await api.get<RegistrationSummaryResponse>(`/elections/${electionId}/registration/summary`);
      setSummary(summ);
      loadVotersList();
    } catch (err: any) {
      alert(err.message || 'Error al aprobar votante.');
    } finally {
      setActionVoterId(null);
    }
  };

  const handleRejectVoter = async () => {
    if (!rejectModalVoter) return;
    try {
      setRejectSubmitting(true);
      await api.post(`/voters/${rejectModalVoter.id}/reject`, {
        reason: rejectionReason || 'Rechazado por administración electoral',
      });
      setRejectModalVoter(null);
      setRejectionReason('');
      await loadPendingVoters();
      const summ = await api.get<RegistrationSummaryResponse>(`/elections/${electionId}/registration/summary`);
      setSummary(summ);
      loadVotersList();
    } catch (err: any) {
      alert(err.message || 'Error al rechazar solicitud.');
    } finally {
      setRejectSubmitting(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'links') {
      loadLinks();
    } else if (activeTab === 'credentials') {
      loadCredentials();
    } else if (activeTab === 'pending-approval') {
      loadPendingVoters();
    }
  }, [activeTab]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadVotersList();
  };

  const handleOpenRegistrationNow = async () => {
    if (!electionId) return;
    if (
      !confirm(
        '¿Confirma la apertura INMEDIATA de la fase de registro? El estado pasará a REGISTRATION_OPEN.'
      )
    ) {
      return;
    }
    try {
      await api.post(`/elections/${electionId}/registration/open-now`);
      await loadBaseData();
    } catch (err: any) {
      alert(err.message || 'Error al abrir la fase de registro.');
    }
  };

  const handleCreateVoter = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!createDocId.trim() || !createFullName.trim() || !createGroupId || !createNodeId) {
      setCreateError('Por favor complete todos los campos obligatorios (*).');
      return;
    }

    let parsedAttrs = {};
    try {
      if (createAttrsText.trim()) {
        parsedAttrs = JSON.parse(createAttrsText);
      }
    } catch {
      setCreateError('El formato JSON de atributos adicionales es inválido.');
      return;
    }

    try {
      setCreateSubmitting(true);
      await api.post(`/elections/${electionId}/voters`, {
        group_id: createGroupId,
        node_id: createNodeId,
        document_id: createDocId.trim(),
        full_name: createFullName.trim(),
        email: createEmail.trim() || null,
        phone: createPhone.trim() || null,
        attributes: parsedAttrs,
      });

      setShowCreateModal(false);
      setCreateDocId('');
      setCreateFullName('');
      setCreateEmail('');
      setCreatePhone('');
      setCreateAttrsText('{}');

      await Promise.all([loadBaseData(), loadVotersList()]);
    } catch (err: any) {
      setCreateError(err.message || 'Error al empadronar votante.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    setImportError(null);
    if (!csvFile) {
      setImportError('Seleccione un archivo CSV para importar.');
      return;
    }

    try {
      setImportSubmitting(true);
      const formData = new FormData();
      formData.append('file', csvFile);

      const batchRes = await api.post<ImportBatch>(
        `/elections/${electionId}/voters/import`,
        formData
      );
      setImportResult(batchRes);
      setCsvFile(null);

      await Promise.all([loadBaseData(), loadVotersList()]);
    } catch (err: any) {
      setImportError(err.message || 'Error en la importación masiva del archivo CSV.');
    } finally {
      setImportSubmitting(false);
    }
  };

  const handleBlockVoter = async () => {
    if (!voterToBlock || !electionId) return;
    try {
      setBlockSubmitting(true);
      await api.patch(`/elections/${electionId}/voters/${voterToBlock.id}`, {
        status: 'BLOCKED',
        blocked_reason: blockReason.trim(),
      });
      setVoterToBlock(null);
      await Promise.all([loadBaseData(), loadVotersList()]);
    } catch (err: any) {
      alert(err.message || 'Error al bloquear votante.');
    } finally {
      setBlockSubmitting(false);
    }
  };

  const handleUnblockVoter = async (voter: Voter) => {
    if (!electionId) return;
    if (!confirm(`¿Confirma el desbloqueo del votante ${voter.full_name} (${voter.document_id})?`)) {
      return;
    }
    try {
      await api.patch(`/elections/${electionId}/voters/${voter.id}`, {
        status: 'IMPORTED',
        blocked_reason: null,
      });
      await Promise.all([loadBaseData(), loadVotersList()]);
    } catch (err: any) {
      alert(err.message || 'Error al desbloquear votante.');
    }
  };

  const handleDeleteVoter = async (voter: Voter) => {
    if (!electionId) return;
    if (
      !confirm(
        `¿Está seguro de retirar y eliminar definitivamente del padrón al votante ${voter.full_name} (${voter.document_id})? Esta acción se registrará en la auditoría inmutable.`
      )
    ) {
      return;
    }
    try {
      await api.delete(`/elections/${electionId}/voters/${voter.id}`);
      await Promise.all([loadBaseData(), loadVotersList()]);
    } catch (err: any) {
      alert(err.message || 'Error al eliminar votante.');
    }
  };

  const handleInspectBatch = async (batchId: string) => {
    if (inspectedBatchId === batchId) {
      setInspectedBatchId(null);
      setInspectedBatchIssues([]);
      return;
    }
    try {
      setInspectedBatchId(batchId);
      setLoadingBatchIssues(true);
      const issues = await api.get<ImportIssue[]>(
        `/elections/${electionId}/voters/import/${batchId}/issues`
      );
      setInspectedBatchIssues(issues);
    } catch (err: any) {
      alert(err.message || 'Error al cargar incidentes del lote.');
    } finally {
      setLoadingBatchIssues(false);
    }
  };

  const loadLinks = async () => {
    if (!electionId) return;
    try {
      const data = await api.get<RegistrationLink[]>(`/elections/${electionId}/registration-links`);
      setLinks(data);
    } catch {
      // silencioso
    }
  };

  const loadCredentials = async () => {
    if (!electionId) return;
    try {
      setCredentialsLoading(true);
      const data = await api.get<CredentialsDispatchResponse>(`/elections/${electionId}/credentials/dispatch`);
      setCredentials(data.credentials);
      setCredentialsTotal(data.total_active_voters);
    } catch {
      // silencioso
    } finally {
      setCredentialsLoading(false);
    }
  };

  const handleCreateLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLinkError(null);
    if (!createLinkGroupId || !createLinkLabel.trim() || !createLinkExpiresAt) {
      setCreateLinkError('Complete los campos obligatorios del enlace.');
      return;
    }
    try {
      setCreateLinkSubmitting(true);
      await api.post(`/elections/${electionId}/registration-links`, {
        group_id: createLinkGroupId,
        node_id: createLinkNodeId || null,
        label: createLinkLabel.trim(),
        expires_at: new Date(createLinkExpiresAt).toISOString(),
        max_uses: createLinkMaxUses ? parseInt(createLinkMaxUses, 10) : null,
      });
      setShowCreateLinkModal(false);
      setCreateLinkLabel('');
      setCreateLinkGroupId('');
      setCreateLinkNodeId('');
      setCreateLinkExpiresAt('');
      setCreateLinkMaxUses('');
      await loadLinks();
    } catch (err: any) {
      setCreateLinkError(err.message || 'Error al generar enlace de registro.');
    } finally {
      setCreateLinkSubmitting(false);
    }
  };

  const handleRevokeLink = async (linkId: string) => {
    if (!window.confirm('¿Desea revocar inmediatamente este enlace de registro?')) return;
    try {
      await api.post(`/elections/${electionId}/registration-links/${linkId}/revoke`);
      await loadLinks();
    } catch (err: any) {
      alert(err.message || 'Error al revocar enlace.');
    }
  };

  const handleSendInvitations = async (groupId?: string) => {
    try {
      setSendingInvitations(true);
      setInvitationsFeedback(null);
      const targetGroup = groupId || groups[0]?.id;
      if (!targetGroup) return;
      const res = await api.post<{ message: string; voters_invited: number }>(
        `/elections/${electionId}/registration-links/send`,
        { group_id: targetGroup }
      );
      setInvitationsFeedback(res.message);
      await Promise.all([loadBaseData(), loadVotersList(), loadLinks()]);
    } catch (err: any) {
      alert(err.message || 'Error al despachar invitaciones.');
    } finally {
      setSendingInvitations(false);
    }
  };

  const handleFreezeRollHash = async () => {
    if (
      !window.confirm(
        '¿Desea congelar el padrón electoral y calcular el roll_hash canónico (SHA-256)? Esta acción cerrará el registro definitivamente.'
      )
    )
      return;
    try {
      setFreezingRoll(true);
      setRollFreezeFeedback(null);
      const res = await api.post<RollHashFreezeResponse>(`/elections/${electionId}/freeze-roll-hash`);
      setRollFreezeFeedback(
        `${res.message} (Huella canónica: ${res.roll_hash.substring(0, 16)}...)`
      );
      await Promise.all([loadBaseData(), loadCredentials()]);
    } catch (err: any) {
      alert(err.message || 'Error al congelar el padrón.');
    } finally {
      setFreezingRoll(false);
    }
  };

  const handleOpenVotingNow = async () => {
    if (
      !window.confirm(
        '¿Desea abrir oficialmente el período de votación (VOTING_OPEN) y emitir las credenciales personales a los votantes activos?'
      )
    )
      return;
    try {
      setOpeningVoting(true);
      await api.post(`/elections/${electionId}/voting/open-now`);
      await Promise.all([loadBaseData(), loadCredentials()]);
    } catch (err: any) {
      alert(err.message || 'Error al abrir la votación.');
    } finally {
      setOpeningVoting(false);
    }
  };

  const copyToClipboard = (text: string, id: string, isCred: boolean = false) => {
    navigator.clipboard.writeText(text);
    if (isCred) {
      setCopiedCredId(id);
      setTimeout(() => setCopiedCredId(null), 2000);
    } else {
      setCopiedLinkId(id);
      setTimeout(() => setCopiedLinkId(null), 2000);
    }
  };

  const handleDownloadCsvTemplate = () => {
    const csvContent =
      'document_id,full_name,email,phone,group_code,node_code,attributes_json\n' +
      '1234567,Juan Perez Mamani,juan.perez@uagrm.edu.bo,71234567,DOCENTES,FICCT_INF,"{""categoria"":""TITULAR""}"\n' +
      '8901234,Maria Elena Rodriguez,maria.rodriguez@uagrm.edu.bo,69876543,ESTUDIANTES,FICCT_SIS,"{""semestre"":8}"\n';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `plantilla_padron_${election?.name.replace(/\s+/g, '_') || 'eleccion'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getVoterStatusBadge = (status: VoterStatus) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3 h-3" />
            <span>Activo</span>
          </span>
        );
      case 'INVITED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase bg-blue-100 text-blue-800">
            <span>Invitado</span>
          </span>
        );
      case 'IMPORTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase bg-stone-100 text-stone-700">
            <span>Importado</span>
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase bg-red-100 text-red-800">
            <Ban className="w-3 h-3" />
            <span>Bloqueado</span>
          </span>
        );
    }
  };

  return (
    <InstitutionalShell activeElectionId={electionId} timezone={election?.timezone}>
      <div className="space-y-6">
        {/* Cabecera y Navegación */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Link
                to="/workspace"
                className="text-xs font-semibold text-stone-500 hover:text-civic-navy-900 flex items-center space-x-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Volver a Elecciones</span>
              </Link>
              <span className="text-stone-300">•</span>
              <span className="text-xs font-mono text-stone-400">ID: {electionId}</span>
            </div>
            <h1 className="font-title text-2xl font-bold text-civic-navy-900 mt-1">
              Padrón Electoral y Registro de Votantes
            </h1>
            <p className="text-xs text-stone-500 mt-0.5">
              Administración de votantes, importación masiva por lotes, control de duplicados IA-L2a y avance de activación.
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => {
                loadBaseData();
                loadVotersList();
              }}
              title="Recargar datos del servidor"
              className="p-2 rounded-lg border border-stone-300 hover:bg-stone-100 text-stone-600 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {isAdminGeneral && isRegistrationOpen && (
              <>
                <button
                  onClick={() => setShowImportModal(true)}
                  className="px-3.5 py-2 rounded-xl text-xs font-bold bg-white border border-stone-300 hover:bg-stone-50 text-stone-800 shadow-xs transition-colors flex items-center space-x-1.5"
                >
                  <Upload className="w-4 h-4 text-seal-amber" />
                  <span>Importar CSV</span>
                </button>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-civic-navy-900 hover:bg-civic-navy-800 text-white shadow-sm transition-colors flex items-center space-x-1.5"
                >
                  <UserPlus className="w-4 h-4 text-seal-emerald" />
                  <span>Nuevo Votante</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Alerta de Estado del Proceso Electoral */}
        {election && (
          <div>
            {election.status === 'DRAFT' && (
              <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 flex items-start space-x-3 shadow-xs">
                <Info className="w-4 h-4 shrink-0 text-amber-700 mt-0.5" />
                <div className="flex-1">
                  <span className="font-bold">Elección en Borrador (DRAFT):</span> Para poder registrar
                  votantes e importar padrones masivos, primero debe publicar solemnemente la elección desde la{' '}
                  <Link
                    to={`/elections/${electionId}/structure`}
                    className="font-bold underline text-amber-950 hover:text-black"
                  >
                    Estructura y Cargos
                  </Link>{' '}
                  o esperar a la fase de registro.
                </div>
              </div>
            )}

            {election.status === 'SCHEDULED' && (
              <div className="p-4 bg-blue-50 border border-blue-300 rounded-xl text-xs text-blue-900 flex items-center justify-between shadow-xs">
                <div className="flex items-center space-x-3">
                  <Calendar className="w-4 h-4 text-blue-700 shrink-0" />
                  <div>
                    <span className="font-bold">Elección Programada (SCHEDULED):</span> La fase de registro
                    iniciará automáticamente el{' '}
                    <span className="font-mono font-bold">
                      {formatElectoralDateTime(election.registration_opens_at, election.timezone)}
                    </span>
                    .
                  </div>
                </div>
                {isAdminGeneral && (
                  <button
                    onClick={handleOpenRegistrationNow}
                    className="px-3.5 py-1.5 bg-seal-emerald hover:bg-emerald-700 text-white font-bold rounded-lg text-xs shadow-xs transition-colors shrink-0 ml-4"
                  >
                    Abrir Registro Ahora
                  </button>
                )}
              </div>
            )}

            {election.status === 'REGISTRATION_OPEN' && (
              <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-xs text-emerald-950 flex items-center justify-between shadow-xs">
                <div className="flex items-center space-x-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-bold">Fase de Registro Abierta:</span> El padrón electoral está en
                    construcción activa y admite altas, bajas, bloqueos e importaciones masivas.
                    <span className="block text-2xs text-emerald-800 font-mono mt-0.5">
                      Cierre programado:{' '}
                      {formatElectoralDateTime(election.registration_closes_at, election.timezone)}
                    </span>
                  </div>
                </div>
                <div className="inline-flex items-center px-3 py-1 bg-emerald-200/70 text-emerald-900 rounded-full font-bold text-2xs uppercase">
                  Padrón en Construcción
                </div>
              </div>
            )}

            {election.status !== 'DRAFT' &&
              election.status !== 'SCHEDULED' &&
              election.status !== 'REGISTRATION_OPEN' && (
                <div className="p-4 bg-stone-100 border border-stone-300 rounded-xl text-xs text-stone-800 flex items-center justify-between shadow-xs">
                  <div className="flex items-center space-x-3">
                    <Lock className="w-5 h-5 text-stone-600 shrink-0" />
                    <div>
                      <span className="font-bold">Padrón Electoral Congelado y Sellado:</span> La fase de
                      registro concluyó. El padrón está inmutable bajo el hash criptográfico oficial
                      (roll_hash). No se admiten altas, bajas ni modificaciones.
                    </div>
                  </div>
                  <div className="inline-flex items-center px-3 py-1 bg-stone-200 text-stone-700 rounded-full font-bold text-2xs uppercase">
                    Padrón Sellado
                  </div>
                </div>
              )}
          </div>
        )}

        {error && (
          <div className="p-4 bg-seal-crimson-light border border-seal-crimson text-seal-crimson-dark text-xs rounded-xl flex items-start space-x-2.5">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Tarjetas KPI y Barra de Progreso */}
        {summary && (
          <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-4 rounded-xl bg-stone-50 border border-stone-200">
                <span className="text-2xs font-bold uppercase text-stone-500 tracking-wider">
                  Total Empadronados
                </span>
                <p className="text-2xl font-black font-mono text-civic-navy-900 mt-1">
                  {summary.total_voters.toLocaleString()}
                </p>
                <span className="text-2xs text-stone-400">Padrón consolidado</span>
              </div>

              <div className="p-4 rounded-xl bg-stone-50 border border-stone-200">
                <span className="text-2xs font-bold uppercase text-stone-500 tracking-wider">
                  Importados
                </span>
                <p className="text-2xl font-black font-mono text-stone-700 mt-1">
                  {summary.imported_count.toLocaleString()}
                </p>
                <span className="text-2xs text-stone-400">Pendientes de invitación</span>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                <span className="text-2xs font-bold uppercase text-emerald-800 tracking-wider">
                  Votantes Activos
                </span>
                <p className="text-2xl font-black font-mono text-emerald-700 mt-1">
                  {summary.active_count.toLocaleString()}
                </p>
                <span className="text-2xs text-emerald-600 font-bold">
                  {summary.activation_percentage.toFixed(1)}% activado
                </span>
              </div>

              <div className="p-4 rounded-xl bg-red-50 border border-red-200">
                <span className="text-2xs font-bold uppercase text-red-800 tracking-wider">
                  Bloqueados
                </span>
                <p className="text-2xl font-black font-mono text-red-700 mt-1">
                  {summary.blocked_count.toLocaleString()}
                </p>
                <span className="text-2xs text-red-600">Inhabilitados</span>
              </div>

              <div
                onClick={() => setActiveTab('duplicates')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  summary.pending_duplicates_count > 0
                    ? 'bg-amber-50 border-amber-300 hover:border-amber-400 hover:shadow-xs'
                    : 'bg-stone-50 border-stone-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-2xs font-bold uppercase text-amber-900 tracking-wider">
                    Alertas IA-L2a
                  </span>
                  {summary.pending_duplicates_count > 0 && (
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                  )}
                </div>
                <p
                  className={`text-2xl font-black font-mono mt-1 ${
                    summary.pending_duplicates_count > 0 ? 'text-amber-700' : 'text-stone-700'
                  }`}
                >
                  {summary.pending_duplicates_count}
                </p>
                <span className="text-2xs text-amber-800 font-semibold flex items-center space-x-1">
                  <span>Posibles duplicados</span>
                  <ChevronRight className="w-3 h-3" />
                </span>
              </div>
            </div>

            {/* Barra de progreso de activación */}
            <div>
              <div className="flex justify-between items-center text-xs font-semibold text-stone-600 mb-1.5">
                <span>Avance de Activación Institucional</span>
                <span className="font-mono font-bold text-civic-navy-900">
                  {summary.active_count} de {summary.total_voters} ({summary.activation_percentage.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full h-3 bg-stone-100 rounded-full overflow-hidden border border-stone-200 flex">
                <div
                  className="h-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, summary.activation_percentage)}%` }}
                />
                <div
                  className="h-full bg-blue-300 transition-all duration-500"
                  style={{
                    width: `${
                      summary.total_voters > 0
                        ? (summary.invited_count / summary.total_voters) * 100
                        : 0
                    }%`,
                  }}
                />
                <div
                  className="h-full bg-red-400 transition-all duration-500"
                  style={{
                    width: `${
                      summary.total_voters > 0
                        ? (summary.blocked_count / summary.total_voters) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
              <div className="flex items-center space-x-4 text-2xs text-stone-500 mt-2 font-mono">
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                  <span>Activo</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-blue-300 inline-block" />
                  <span>Invitado</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-stone-300 inline-block" />
                  <span>Importado</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
                  <span>Bloqueado</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Pestañas de Navegación Interna */}
        <div className="border-b border-stone-200 flex items-center space-x-6 text-xs font-bold">
          <button
            onClick={() => setActiveTab('voters')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'voters'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Padrón de Votantes ({voters.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('import')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'import'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Lotes de Importación CSV ({batches.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('duplicates')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'duplicates'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>Arbitraje de Duplicados IA-L2a</span>
            {pendingDuplicates.length > 0 && (
              <span className="px-1.5 py-0.2 bg-amber-200 text-amber-900 rounded-full font-mono text-2xs">
                {pendingDuplicates.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('breakdown')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'breakdown'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Desglose por Grupo y Nodo</span>
          </button>

          <button
            onClick={() => setActiveTab('links')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'links'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Link2 className="w-4 h-4 text-emerald-600" />
            <span>Enlaces de Registro S1-08 ({links.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('credentials')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'credentials'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Key className="w-4 h-4 text-civic-navy-900" />
            <span>Credenciales Demo S1-09 ({credentials.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('pending-approval')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'pending-approval'
                ? 'border-civic-navy-900 text-civic-navy-900'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <UserPlus className="w-4 h-4 text-seal-amber" />
            <span>
              Autoinscripciones S2-10
              {pendingVoters.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] bg-seal-amber text-white font-bold">
                  {pendingVoters.length}
                </span>
              )}
            </span>
          </button>
        </div>

        {/* PESTAÑA 1: PADRÓN DE VOTANTES */}
        {activeTab === 'voters' && (
          <div className="space-y-4">
            {/* Barra de Filtros y Búsqueda */}
            <div className="bg-white border border-stone-300 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
              <form onSubmit={handleSearchSubmit} className="flex-1 w-full flex items-center space-x-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-stone-400" />
                  <input
                    type="text"
                    placeholder="Buscar por Cédula de Identidad (CI) o Nombre Completo..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-civic-navy-900/20"
                  />
                </div>
                <button
                  type="submit"
                  className="px-3.5 py-2 bg-stone-100 hover:bg-stone-200 border border-stone-300 rounded-lg text-xs font-semibold text-stone-700"
                >
                  Filtrar
                </button>
              </form>

              <div className="flex items-center space-x-2 w-full md:w-auto">
                <select
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(e.target.value)}
                  className="text-xs border border-stone-300 rounded-lg p-2 bg-white"
                >
                  <option value="">Todos los Grupos</option>
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name} ({g.code})
                    </option>
                  ))}
                </select>

                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="text-xs border border-stone-300 rounded-lg p-2 bg-white font-mono"
                >
                  <option value="">Todos los Estados</option>
                  <option value="IMPORTED">IMPORTED</option>
                  <option value="INVITED">INVITED</option>
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="BLOCKED">BLOCKED</option>
                </select>
              </div>
            </div>

            {/* Tabla del Padrón */}
            <div className="bg-white border border-stone-300 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-stone-50 border-b border-stone-200 text-stone-600 font-bold uppercase text-2xs tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Documento (CI)</th>
                      <th className="px-4 py-3">Nombre Completo</th>
                      <th className="px-4 py-3">Grupo / Carrera</th>
                      <th className="px-4 py-3">Ruta Jerárquica</th>
                      <th className="px-4 py-3">Contacto</th>
                      <th className="px-4 py-3">Estado</th>
                      <th className="px-4 py-3 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200">
                    {tableLoading ? (
                      <tr>
                        <td colSpan={7} className="p-8 text-center text-stone-400 font-mono">
                          Cargando votantes del padrón...
                        </td>
                      </tr>
                    ) : voters.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="p-8 text-center text-stone-400 font-sans">
                          No se encontraron votantes empadronados con los filtros aplicados.
                        </td>
                      </tr>
                    ) : (
                      voters.map((voter) => (
                        <tr key={voter.id} className="hover:bg-stone-50/70 transition-colors">
                          <td className="px-4 py-3 font-mono font-bold text-civic-navy-900">
                            {voter.document_id}
                          </td>
                          <td className="px-4 py-3 font-medium text-stone-800">
                            {voter.full_name}
                          </td>
                          <td className="px-4 py-3 text-stone-600">
                            {voter.group_name || 'N/A'}
                          </td>
                          <td className="px-4 py-3 font-mono text-2xs text-stone-500">
                            {voter.node_path || voter.node_name || 'N/A'}
                          </td>
                          <td className="px-4 py-3 text-stone-500 text-2xs">
                            <div>{voter.email || '—'}</div>
                            {voter.phone && <div className="text-stone-400 font-mono">{voter.phone}</div>}
                          </td>
                          <td className="px-4 py-3">
                            {getVoterStatusBadge(voter.status)}
                            {voter.status === 'BLOCKED' && voter.blocked_reason && (
                              <div className="text-3xs text-red-600 mt-0.5 line-clamp-1 italic">
                                {voter.blocked_reason}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right space-x-2">
                            {isAdminGeneral && isRegistrationOpen && (
                              <>
                                {voter.status === 'BLOCKED' ? (
                                  <button
                                    onClick={() => handleUnblockVoter(voter)}
                                    title="Desbloquear votante"
                                    className="p-1 rounded text-emerald-700 hover:bg-emerald-50"
                                  >
                                    <Check className="w-3.5 h-3.5" />
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => setVoterToBlock(voter)}
                                    title="Bloquear votante"
                                    className="p-1 rounded text-red-600 hover:bg-red-50"
                                  >
                                    <Ban className="w-3.5 h-3.5" />
                                  </button>
                                )}
                                <button
                                  onClick={() => handleDeleteVoter(voter)}
                                  title="Eliminar y retirar del padrón"
                                  className="p-1 rounded text-stone-400 hover:text-red-700 hover:bg-red-50"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* PESTAÑA 2: LOTES DE IMPORTACIÓN CSV */}
        {activeTab === 'import' && (
          <div className="space-y-6">
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="font-title text-base font-bold text-civic-navy-900">
                  Carga Masiva de Padrón Electoral
                </h3>
                <p className="text-xs text-stone-500 mt-1 max-w-xl">
                  Importe archivos CSV con votantes. El sistema valida automáticamente que el nodo pertenezca
                  al nivel más profundo requerido, detecta posibles duplicados mediante IA-L2a y registra
                  un lote de auditoría.
                </p>
              </div>
              <div className="flex items-center space-x-3 shrink-0">
                <button
                  onClick={handleDownloadCsvTemplate}
                  className="px-3.5 py-2 rounded-xl text-xs font-semibold border border-stone-300 hover:bg-stone-50 text-stone-700 flex items-center space-x-1.5"
                >
                  <Download className="w-4 h-4 text-stone-500" />
                  <span>Descargar Plantilla CSV</span>
                </button>
                {isAdminGeneral && isRegistrationOpen && (
                  <button
                    onClick={() => setShowImportModal(true)}
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-civic-navy-900 hover:bg-civic-navy-800 text-white shadow-xs flex items-center space-x-1.5"
                  >
                    <Upload className="w-4 h-4 text-seal-amber" />
                    <span>Subir Archivo CSV</span>
                  </button>
                )}
              </div>
            </div>

            {/* Listado de Lotes */}
            <div className="bg-white border border-stone-300 rounded-xl overflow-hidden shadow-sm">
              <div className="px-6 py-4 bg-stone-50 border-b border-stone-200">
                <h4 className="font-title text-xs font-bold text-stone-700 uppercase tracking-wider">
                  Historial de Lotes Procesados
                </h4>
              </div>
              <div className="divide-y divide-stone-200">
                {batches.length === 0 ? (
                  <div className="p-8 text-center text-stone-400 text-xs font-sans">
                    No se han realizado cargas masivas de padrón aún.
                  </div>
                ) : (
                  batches.map((b) => (
                    <div key={b.id} className="p-5 hover:bg-stone-50/50 transition-colors space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center space-x-3">
                          <FileSpreadsheet className="w-8 h-8 text-emerald-600 shrink-0" />
                          <div>
                            <span className="font-title font-bold text-sm text-civic-navy-900">
                              {b.filename}
                            </span>
                            <div className="text-2xs font-mono text-stone-400">
                              Lote ID: {b.id} • {formatElectoralDateTime(b.created_at, election?.timezone)}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-4">
                          <div className="flex items-center space-x-3 text-xs font-mono">
                            <span className="text-stone-600">Total: <strong>{b.total_rows}</strong></span>
                            <span className="text-emerald-700">Válidos: <strong>{b.valid_rows}</strong></span>
                            {b.error_rows > 0 && (
                              <span className="text-red-700 font-bold">Errores: {b.error_rows}</span>
                            )}
                            {b.duplicate_warnings > 0 && (
                              <span className="text-amber-700 font-bold">Alertas: {b.duplicate_warnings}</span>
                            )}
                          </div>

                          {(b.error_rows > 0 || b.duplicate_warnings > 0) && (
                            <button
                              onClick={() => handleInspectBatch(b.id)}
                              className="px-2.5 py-1 text-2xs font-bold rounded border border-stone-300 hover:bg-stone-100 text-stone-700"
                            >
                              {inspectedBatchId === b.id ? 'Ocultar Detalles' : 'Ver Incidentes'}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Desglose de Incidentes del Lote */}
                      {inspectedBatchId === b.id && (
                        <div className="mt-3 p-4 bg-stone-50 rounded-xl border border-stone-200 space-y-3 animate-in fade-in duration-150">
                          <h5 className="font-mono text-2xs font-bold text-stone-700 uppercase">
                            Incidentes y Alertas del Lote #{b.id}
                          </h5>
                          {loadingBatchIssues ? (
                            <div className="text-xs text-stone-400 font-mono">Cargando incidentes...</div>
                          ) : inspectedBatchIssues.length === 0 ? (
                            <div className="text-xs text-stone-500">No se registraron incidentes para este lote.</div>
                          ) : (
                            <div className="space-y-2">
                              {inspectedBatchIssues.map((issue) => (
                                <div
                                  key={issue.id}
                                  className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                                    issue.issue_type === 'POSSIBLE_DUPLICATE'
                                      ? 'bg-amber-50/70 border-amber-200 text-amber-950'
                                      : 'bg-red-50/70 border-red-200 text-red-950'
                                  }`}
                                >
                                  <div>
                                    <div className="flex items-center space-x-2">
                                      <span className="font-mono font-bold text-2xs px-1.5 py-0.5 rounded bg-white/80 border">
                                        Fila #{issue.row_number}
                                      </span>
                                      <span className="font-bold">
                                        {issue.issue_type === 'POSSIBLE_DUPLICATE'
                                          ? 'Posible Duplicado (IA-L2a)'
                                          : 'Error de Validación'}
                                      </span>
                                      <span className="font-mono text-stone-600">CI: {issue.document_id || '—'}</span>
                                    </div>
                                    <p className="text-2xs text-stone-600 mt-1">
                                      {issue.raw_full_name} —{' '}
                                      {JSON.stringify(issue.details)}
                                    </p>
                                  </div>

                                  {issue.issue_type === 'POSSIBLE_DUPLICATE' && issue.resolution === 'PENDING' && (
                                    <button
                                      onClick={() => setSelectedDuplicateIssue(issue)}
                                      className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded font-bold text-2xs shrink-0 ml-3"
                                    >
                                      Arbitrar Dictamen
                                    </button>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* PESTAÑA 3: ARBITRAJE DE DUPLICADOS IA-L2a */}
        {activeTab === 'duplicates' && (
          <div className="space-y-4">
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex items-start space-x-4">
              <div className="p-3 bg-amber-100 text-amber-800 rounded-xl">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="font-title text-base font-bold text-civic-navy-900">
                  Bandeja de Arbitraje de Duplicados (IA-L2a)
                </h3>
                <p className="text-xs text-stone-600 mt-1">
                  El detector asistido por similitud trigram (<code className="font-mono">pg_trgm</code>) y distancia Levenshtein ha
                  marcado registros con alta probabilidad de homonimia o duplicidad en el padrón. El tribunal electoral debe emitir
                  un dictamen soberano e irrevocable para cada caso.
                </p>
              </div>
            </div>

            <div className="bg-white border border-stone-300 rounded-xl overflow-hidden shadow-sm">
              <div className="divide-y divide-stone-200">
                {pendingDuplicates.length === 0 ? (
                  <div className="p-12 text-center text-stone-400 text-xs font-sans space-y-2">
                    <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
                    <p className="font-bold text-stone-700">No hay alertas de duplicados pendientes</p>
                    <p className="text-stone-400">El padrón no presenta colisiones de homonimia no resueltas.</p>
                  </div>
                ) : (
                  pendingDuplicates.map((issue) => {
                    const simPct = Math.round((issue.similarity_score || 0) * 100);
                    return (
                      <div
                        key={issue.id}
                        className="p-5 hover:bg-stone-50/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                      >
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-2xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                              Similitud: {simPct}%
                            </span>
                            <span className="font-mono text-2xs text-stone-500">
                              Distancia Levenshtein: {issue.edit_distance ?? 'N/A'} chars
                            </span>
                            <span className="text-2xs text-stone-400">• Fila #{issue.row_number}</span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                            <div className="p-3 bg-amber-50/50 border border-amber-200 rounded-lg text-xs">
                              <span className="text-2xs font-bold text-amber-800 uppercase block">
                                Registro Evaluado (Entrante)
                              </span>
                              <p className="font-bold text-stone-900 mt-0.5">
                                {issue.candidate_voter_name || issue.raw_full_name}
                              </p>
                              <span className="font-mono text-2xs text-stone-600 block mt-0.5">
                                CI: {issue.document_id || 'N/A'}
                              </span>
                            </div>

                            <div className="p-3 bg-stone-50 border border-stone-200 rounded-lg text-xs">
                              <span className="text-2xs font-bold text-stone-600 uppercase block">
                                Registro Pre-Existente en Padrón
                              </span>
                              <p className="font-bold text-stone-900 mt-0.5">
                                {issue.matched_voter_name || 'Votante Registrado'}
                              </p>
                              <span className="font-mono text-2xs text-stone-600 block mt-0.5">
                                CI: {issue.matched_voter_document || 'N/A'}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="shrink-0 flex items-center">
                          {isAdminGeneral && (
                            <button
                              onClick={() => setSelectedDuplicateIssue(issue)}
                              className="px-4 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-xl text-xs font-bold shadow-xs transition-colors flex items-center space-x-1.5"
                            >
                              <span>Emitir Dictamen</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* PESTAÑA 4: DESGLOSE POR GRUPO Y NODO */}
        {activeTab === 'breakdown' && summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Desglose por Grupos de Votantes */}
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm space-y-4">
              <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                <Users className="w-4 h-4 text-seal-emerald" />
                <span>Consolidado por Grupos de Votantes</span>
              </h3>
              <div className="space-y-3">
                {summary.by_group.map((g) => (
                  <div key={g.group_id} className="p-4 bg-stone-50 rounded-xl border border-stone-200 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-stone-900 text-xs">
                        {g.group_name} ({g.group_code})
                      </span>
                      <span className="font-mono font-bold text-xs text-civic-navy-900">
                        {g.total_voters} votantes
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-2xs font-mono text-stone-600">
                      <div>Activos: <strong className="text-emerald-700">{g.active_count}</strong></div>
                      <div>Invitados: <strong>{g.invited_count}</strong></div>
                      <div>Bloqueados: <strong className="text-red-700">{g.blocked_count}</strong></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Desglose por Nodos Jerárquicos */}
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm space-y-4">
              <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-seal-amber" />
                <span>Consolidado por Nodos Jerárquicos</span>
              </h3>
              <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {summary.by_node.map((n) => (
                  <div key={n.node_id} className="p-3 bg-stone-50 rounded-xl border border-stone-200 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-stone-900">{n.node_name}</span>
                      <span className="font-mono font-bold text-civic-navy-900">
                        {n.total_voters} ({n.active_voters} activos)
                      </span>
                    </div>
                    <div className="font-mono text-3xs text-stone-400 truncate">
                      {n.node_path}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* PESTAÑA 5: ENLACES DE REGISTRO (S1-08) */}
        {activeTab === 'links' && (
          <div className="space-y-4">
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                  <Link2 className="w-5 h-5 text-emerald-600" />
                  <span>Gestión de Enlaces Públicos de Registro (S1-08)</span>
                </h3>
                <p className="text-xs text-stone-500 mt-1 max-w-xl">
                  Cree enlaces públicos con tokens URL-safe de alta entropía asignados a un grupo o rama territorial. Los ciudadanos empadronados podrán confirmar su CI para activar su registro.
                </p>
              </div>

              {isAdminGeneral && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleSendInvitations()}
                    disabled={sendingInvitations || links.length === 0}
                    className="px-3.5 py-2 bg-stone-100 hover:bg-stone-200 border border-stone-300 text-stone-800 text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
                  >
                    <Send className="w-3.5 h-3.5 text-blue-600" />
                    <span>{sendingInvitations ? 'Despachando...' : 'Despachar Invitaciones'}</span>
                  </button>

                  <button
                    onClick={() => setShowCreateLinkModal(true)}
                    className="px-4 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm"
                  >
                    <Link2 className="w-3.5 h-3.5" />
                    <span>Nuevo Enlace</span>
                  </button>
                </div>
              )}
            </div>

            {invitationsFeedback && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-blue-600 flex-shrink-0" />
                <span>{invitationsFeedback}</span>
              </div>
            )}

            {/* Tabla de Enlaces */}
            <div className="bg-white border border-stone-300 rounded-xl shadow-electoral overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-civic-navy-900 text-stone-300 uppercase font-mono text-[10px] tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Etiqueta / Descripción</th>
                      <th className="py-3 px-4">Grupo / Nodo Objetivo</th>
                      <th className="py-3 px-4">URL de Activación</th>
                      <th className="py-3 px-4 text-center">Usos</th>
                      <th className="py-3 px-4 text-center">Estado</th>
                      <th className="py-3 px-4">Vencimiento</th>
                      <th className="py-3 px-4 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200">
                    {links.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-stone-500">
                          No existen enlaces de registro activos. Haga clic en <strong>Nuevo Enlace</strong> para generar uno.
                        </td>
                      </tr>
                    ) : (
                      links.map((link) => {
                        const fullUrl = `${window.location.origin}/register/${link.raw_token || link.token_hash}`;
                        const isCopied = copiedLinkId === link.id;
                        return (
                          <tr key={link.id} className="hover:bg-stone-50/80 transition-colors">
                            <td className="py-3 px-4 font-semibold text-stone-900">
                              {link.label}
                            </td>
                            <td className="py-3 px-4 text-stone-600">
                              <span className="font-bold text-stone-800">{link.group_name || 'Grupo'}</span>
                              {link.node_name && (
                                <span className="block text-2xs font-mono text-stone-400">
                                  {link.node_name}
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4 font-mono text-2xs text-stone-600">
                              <div className="flex items-center space-x-1.5 bg-stone-100 px-2 py-1 rounded max-w-xs truncate">
                                <span className="truncate">{fullUrl}</span>
                                <button
                                  type="button"
                                  onClick={() => copyToClipboard(fullUrl, link.id)}
                                  className="text-stone-500 hover:text-stone-900 p-0.5"
                                  title="Copiar URL"
                                >
                                  {isCopied ? (
                                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-center font-mono">
                              {link.uses_count} / {link.max_uses !== null ? link.max_uses : '∞'}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <span
                                className={`px-2 py-0.5 rounded-full text-3xs font-bold uppercase font-mono ${
                                  link.status === 'ACTIVE'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : link.status === 'EXPIRED'
                                    ? 'bg-stone-100 text-stone-600'
                                    : 'bg-red-100 text-red-800'
                                }`}
                              >
                                {link.status}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-stone-500 text-2xs font-mono">
                              {formatElectoralDateTime(link.expires_at)}
                            </td>
                            <td className="py-3 px-4 text-right">
                              {link.status === 'ACTIVE' && isAdminGeneral && (
                                <button
                                  type="button"
                                  onClick={() => handleRevokeLink(link.id)}
                                  className="text-red-600 hover:text-red-800 font-bold text-xs"
                                >
                                  Revocar
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* PESTAÑA 6: CREDENCIALES DEMO (S1-09) */}
        {activeTab === 'credentials' && (
          <div className="space-y-4">
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                    <Key className="w-5 h-5 text-civic-navy-900" />
                    <span>Despacho de Credenciales Personales de Votación (S1-09)</span>
                  </h3>
                  {election?.roll_hash && (
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-900 rounded font-mono text-2xs font-bold">
                      Padrón Congelado
                    </span>
                  )}
                </div>
                <p className="text-xs text-stone-500 mt-1 max-w-xl">
                  Credenciales de un solo uso emitidas a votantes <strong>ACTIVE</strong> al abrirse el período de sufragio. En entorno de evaluación académica, puede copiar el código para ingresar a la Cabina de Votación (<strong>/vote</strong>).
                </p>
              </div>

              {isAdminGeneral && (
                <div className="flex flex-wrap items-center gap-2">
                  {!election?.roll_hash && (
                    <button
                      onClick={handleFreezeRollHash}
                      disabled={freezingRoll}
                      className="px-3.5 py-2 bg-stone-800 hover:bg-stone-900 text-white text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
                    >
                      <Lock className="w-3.5 h-3.5 text-amber-400" />
                      <span>{freezingRoll ? 'Congelando...' : 'Congelar Padrón (roll_hash)'}</span>
                    </button>
                  )}

                  {election?.status !== 'VOTING_OPEN' && election?.status !== 'VOTING_CLOSED' && (
                    <button
                      onClick={handleOpenVotingNow}
                      disabled={openingVoting}
                      className="px-3.5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{openingVoting ? 'Abriendo...' : 'Abrir Votación Ahora'}</span>
                    </button>
                  )}

                  <Link
                    to="/vote"
                    target="_blank"
                    className="px-3.5 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Abrir Cabina (/vote)</span>
                  </Link>
                </div>
              )}
            </div>

            {rollFreezeFeedback && (
              <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg text-xs text-emerald-900 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{rollFreezeFeedback}</span>
              </div>
            )}

            {/* Tabla de Credenciales */}
            <div className="bg-white border border-stone-300 rounded-xl shadow-electoral overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-civic-navy-900 text-stone-300 uppercase font-mono text-[10px] tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Documento (CI)</th>
                      <th className="py-3 px-4">Votante Habilitado</th>
                      <th className="py-3 px-4">Grupo / Segmento</th>
                      <th className="py-3 px-4">Código Credencial Personal</th>
                      <th className="py-3 px-4 text-center">Estado Uso</th>
                      <th className="py-3 px-4 text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200">
                    {credentialsLoading ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-stone-500">
                          Cargando credenciales despachadas...
                        </td>
                      </tr>
                    ) : credentials.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-stone-500">
                          Aún no se han emitido credenciales. Las credenciales se generan al abrirse la votación oficial (<strong>VOTING_OPEN</strong>).
                        </td>
                      </tr>
                    ) : (
                      credentials.map((cred) => {
                        const isCopied = copiedCredId === cred.voter_id;
                        return (
                          <tr key={cred.voter_id} className="hover:bg-stone-50/80 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-stone-900">
                              {cred.document_id}
                            </td>
                            <td className="py-3 px-4 font-semibold text-stone-800">
                              {cred.full_name}
                            </td>
                            <td className="py-3 px-4 text-stone-600">
                              <span>{cred.group_name}</span>
                              <span className="block text-3xs font-mono text-stone-400">
                                {cred.node_path}
                              </span>
                            </td>
                            <td className="py-3 px-4 font-mono text-xs">
                              <span className="bg-stone-100 text-civic-navy-900 px-2 py-1 rounded font-bold tracking-wider">
                                {cred.credential_code}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-center">
                              {cred.is_used ? (
                                <span className="px-2 py-0.5 rounded-full text-3xs font-bold uppercase font-mono bg-stone-100 text-stone-500">
                                  Utilizada
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-3xs font-bold uppercase font-mono bg-emerald-100 text-emerald-800">
                                  Disponible
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                type="button"
                                onClick={() => copyToClipboard(cred.credential_code, cred.voter_id, true)}
                                className="px-2.5 py-1 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded text-2xs font-bold flex items-center space-x-1 ml-auto"
                              >
                                {isCopied ? (
                                  <>
                                    <Check className="w-3 h-3 text-emerald-600" />
                                    <span>¡Copiado!</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3 h-3" />
                                    <span>Copiar</span>
                                  </>
                                )}
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* PESTAÑA: SOLICITUDES DE AUTOINSCRIPCIÓN (S2-10) */}
        {activeTab === 'pending-approval' && (
          <div className="space-y-4">
            <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                  <UserPlus className="w-5 h-5 text-seal-amber" />
                  <span>Bandeja de Aprobación de Autoinscripciones (S2-10)</span>
                </h3>
                <p className="text-xs text-stone-600 mt-1 max-w-2xl">
                  Revisa y valida las solicitudes ciudadanas registradas en la modalidad abierta con aprobación
                  (`OPEN_WITH_APPROVAL`). Al aprobar un registro, pasa a estado ACTIVO y se integrará al Árbol de Merkle
                  del padrón.
                </p>
              </div>

              <button
                onClick={loadPendingVoters}
                disabled={loadingPending}
                className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingPending ? 'animate-spin' : ''}`} />
                <span>Actualizar Solicitudes</span>
              </button>
            </div>

            <div className="bg-white border border-stone-300 rounded-xl overflow-hidden shadow-sm">
              <div className="p-3 bg-stone-50 border-b border-stone-200 text-xs font-bold text-stone-700 flex justify-between items-center">
                <span>Solicitudes Pendientes de Revisión ({pendingVoters.length})</span>
                <span className="text-[11px] font-mono text-stone-500">Modo: {election?.registration_mode}</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-stone-100 text-stone-600 font-mono text-[11px] border-b border-stone-200">
                      <th className="py-2.5 px-3">Documento (CI)</th>
                      <th className="py-2.5 px-3">Nombre Completo</th>
                      <th className="py-2.5 px-3">Contacto</th>
                      <th className="py-2.5 px-3">Grupo / Nodo</th>
                      <th className="py-2.5 px-3">Fecha Solicitud</th>
                      <th className="py-2.5 px-3 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200">
                    {pendingVoters.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-xs text-stone-500 font-mono">
                          No hay solicitudes de autoinscripción pendientes de aprobación.
                        </td>
                      </tr>
                    ) : (
                      pendingVoters.map((v) => {
                        const grp = groups.find((g) => g.id === v.group_id);
                        const nde = nodes.find((n) => n.id === v.node_id);
                        const isActing = actionVoterId === v.id;

                        return (
                          <tr key={v.id} className="hover:bg-stone-50">
                            <td className="py-2.5 px-3 font-mono font-bold text-civic-navy-900">
                              {v.document_id}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-stone-800">
                              {v.full_name}
                            </td>
                            <td className="py-2.5 px-3 text-stone-600 font-mono text-[11px]">
                              <div>{v.email || 'Sin correo'}</div>
                              {v.phone && <div className="text-stone-400">{v.phone}</div>}
                            </td>
                            <td className="py-2.5 px-3 text-stone-700">
                              <span className="font-semibold block">{grp?.name || v.group_id}</span>
                              <span className="text-[10px] text-stone-500 font-mono">
                                {nde?.name || v.node_id} ({nde?.path || ''})
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-stone-500 font-mono text-[11px]">
                              {new Date(v.created_at).toLocaleString()}
                            </td>
                            <td className="py-2.5 px-3 text-right space-x-1.5 whitespace-nowrap">
                              <button
                                onClick={() => handleApproveVoter(v.id)}
                                disabled={isActing}
                                className="px-2.5 py-1 bg-seal-emerald hover:bg-seal-emerald/90 text-white rounded text-xs font-bold transition-colors disabled:opacity-50"
                              >
                                {isActing ? 'Procesando...' : 'Aprobar'}
                              </button>
                              <button
                                onClick={() => {
                                  setRejectModalVoter(v);
                                  setRejectionReason('No cumple con los requisitos institucionales del padrón.');
                                }}
                                disabled={isActing}
                                className="px-2.5 py-1 bg-red-100 hover:bg-red-200 text-red-800 rounded text-xs font-bold transition-colors disabled:opacity-50"
                              >
                                Rechazar
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: EMPADRONAR VOTANTE INDIVIDUAL */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-xs p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl border border-stone-300 shadow-2xl max-w-lg w-full p-6 space-y-4 my-8">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                  <UserPlus className="w-5 h-5 text-seal-emerald" />
                  <span>Alta Individual de Votante</span>
                </h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-stone-400 hover:text-stone-600 font-bold text-xl"
                >
                  &times;
                </button>
              </div>

              {createError && (
                <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                  {createError}
                </div>
              )}

              <form onSubmit={handleCreateVoter} className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1">Cédula de Identidad (CI) *</label>
                    <input
                      type="text"
                      required
                      placeholder="Ej. 1234567 SC"
                      value={createDocId}
                      onChange={(e) => setCreateDocId(e.target.value)}
                      className="w-full border p-2 rounded-lg font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold mb-1">Nombre Completo *</label>
                    <input
                      type="text"
                      required
                      placeholder="Ej. Juan Perez Mamani"
                      value={createFullName}
                      onChange={(e) => setCreateFullName(e.target.value)}
                      className="w-full border p-2 rounded-lg"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1">Grupo de Votantes *</label>
                    <select
                      required
                      value={createGroupId}
                      onChange={(e) => setCreateGroupId(e.target.value)}
                      className="w-full border p-2 rounded-lg bg-white"
                    >
                      <option value="">Seleccione Grupo...</option>
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name} ({g.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold mb-1">Nodo Jerárquico *</label>
                    <select
                      required
                      value={createNodeId}
                      onChange={(e) => setCreateNodeId(e.target.value)}
                      className="w-full border p-2 rounded-lg bg-white"
                    >
                      <option value="">Seleccione Nodo...</option>
                      {nodes
                        .filter((n) => !createGroupId || n.group_id === createGroupId)
                        .map((n) => (
                          <option key={n.id} value={n.id}>
                            {n.path || n.name}
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1">Correo Electrónico (Opcional)</label>
                    <input
                      type="email"
                      placeholder="juan.perez@uagrm.edu.bo"
                      value={createEmail}
                      onChange={(e) => setCreateEmail(e.target.value)}
                      className="w-full border p-2 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold mb-1">Teléfono (Opcional)</label>
                    <input
                      type="tel"
                      placeholder="71234567"
                      value={createPhone}
                      onChange={(e) => setCreatePhone(e.target.value)}
                      className="w-full border p-2 rounded-lg font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold mb-1">
                    Atributos Extra Dinámicos (JSON)
                  </label>
                  <textarea
                    rows={2}
                    value={createAttrsText}
                    onChange={(e) => setCreateAttrsText(e.target.value)}
                    placeholder='{"categoria": "TITULAR", "semestre": 5}'
                    className="w-full border p-2 rounded-lg font-mono text-2xs"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-3 border-t">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-3.5 py-2 border rounded-lg text-stone-600 hover:bg-stone-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={createSubmitting}
                    className="px-4 py-2 bg-civic-navy-900 text-white rounded-lg font-bold shadow-xs disabled:opacity-50"
                  >
                    {createSubmitting ? 'Guardando...' : 'Registrar Votante'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: CARGA MASIVA CSV */}
        {showImportModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-xs p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl border border-stone-300 shadow-2xl max-w-lg w-full p-6 space-y-4 my-8">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                  <Upload className="w-5 h-5 text-seal-amber" />
                  <span>Importación Masiva de Padrón CSV</span>
                </h3>
                <button
                  onClick={() => {
                    setShowImportModal(false);
                    setImportResult(null);
                  }}
                  className="text-stone-400 hover:text-stone-600 font-bold text-xl"
                >
                  &times;
                </button>
              </div>

              {importError && (
                <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                  {importError}
                </div>
              )}

              {importResult ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-3 text-xs">
                  <div className="flex items-center space-x-2 text-emerald-800 font-bold">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>Lote de Importación Procesado Exitosamente</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-stone-700 font-mono text-2xs">
                    <div>Filas Leídas: <strong>{importResult.total_rows}</strong></div>
                    <div>Filas Válidas: <strong className="text-emerald-700">{importResult.valid_rows}</strong></div>
                    <div>Filas con Error: <strong className="text-red-700">{importResult.error_rows}</strong></div>
                    <div>Alertas Duplicado: <strong className="text-amber-700">{importResult.duplicate_warnings}</strong></div>
                  </div>
                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={() => {
                        setShowImportModal(false);
                        setImportResult(null);
                      }}
                      className="px-4 py-2 bg-civic-navy-900 text-white rounded-lg font-bold text-xs"
                    >
                      Aceptar y Cerrar
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleImportCsv} className="space-y-4 text-xs">
                  <div className="p-4 border-2 border-dashed border-stone-300 rounded-xl text-center space-y-2 hover:border-civic-navy-900/50 transition-colors">
                    <Upload className="w-8 h-8 text-stone-400 mx-auto" />
                    <label className="cursor-pointer block">
                      <span className="font-semibold text-civic-navy-900 hover:underline">
                        Haga clic para seleccionar archivo CSV
                      </span>
                      <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                        className="hidden"
                      />
                    </label>
                    <span className="text-2xs text-stone-400 block">
                      {csvFile ? csvFile.name : 'Formato requerido UTF-8 con cabecera'}
                    </span>
                  </div>

                  <div className="p-3 bg-stone-50 rounded-lg border text-2xs text-stone-600 space-y-1">
                    <span className="font-bold block">Cabeceras esperadas:</span>
                    <code className="font-mono block text-3xs text-stone-800 bg-white p-1 rounded border">
                      document_id,full_name,email,phone,group_code,node_code,attributes_json
                    </code>
                  </div>

                  <div className="flex justify-end space-x-2 pt-3 border-t">
                    <button
                      type="button"
                      onClick={() => setShowImportModal(false)}
                      className="px-3.5 py-2 border rounded-lg text-stone-600 hover:bg-stone-50"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={importSubmitting || !csvFile}
                      className="px-4 py-2 bg-civic-navy-900 text-white rounded-lg font-bold shadow-xs disabled:opacity-50"
                    >
                      {importSubmitting ? 'Procesando Lote...' : 'Subir y Procesar'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* MODAL: BLOQUEAR VOTANTE */}
        {voterToBlock && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl border border-stone-300 shadow-2xl max-w-md w-full p-6 space-y-4">
              <h3 className="font-title text-base font-bold text-red-900 flex items-center space-x-2">
                <Ban className="w-5 h-5 text-red-600" />
                <span>Bloquear Votante del Padrón</span>
              </h3>
              <p className="text-xs text-stone-600">
                Está a punto de inhabilitar a{' '}
                <strong className="text-stone-900">{voterToBlock.full_name}</strong> (CI:{' '}
                <code className="font-mono">{voterToBlock.document_id}</code>).
              </p>

              <div>
                <label className="block text-xs font-semibold mb-1 text-stone-700">
                  Motivo de inhabilitación o bloqueo:
                </label>
                <textarea
                  rows={2}
                  value={blockReason}
                  onChange={(e) => setBlockReason(e.target.value)}
                  className="w-full text-xs border border-stone-300 rounded-lg p-2"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setVoterToBlock(null)}
                  className="px-3.5 py-2 border rounded-lg text-stone-600 hover:bg-stone-50 text-xs"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={blockSubmitting}
                  onClick={handleBlockVoter}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-xs shadow-xs disabled:opacity-50"
                >
                  {blockSubmitting ? 'Bloqueando...' : 'Confirmar Bloqueo'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: GENERAR ENLACE DE REGISTRO (S1-08) */}
        {showCreateLinkModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-xs p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl border border-stone-300 shadow-2xl max-w-lg w-full p-6 space-y-4 my-8">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                  <Link2 className="w-5 h-5 text-emerald-600" />
                  <span>Crear Enlace Público de Registro</span>
                </h3>
                <button
                  onClick={() => setShowCreateLinkModal(false)}
                  className="text-stone-400 hover:text-stone-600 font-bold text-xl"
                >
                  &times;
                </button>
              </div>

              {createLinkError && (
                <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                  {createLinkError}
                </div>
              )}

              <form onSubmit={handleCreateLink} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold mb-1 text-stone-700">
                    Etiqueta / Descripción del Enlace *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Ej. Registro Estudiantes de Informática 2026"
                    value={createLinkLabel}
                    onChange={(e) => setCreateLinkLabel(e.target.value)}
                    className="w-full border border-stone-300 p-2 rounded-lg"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1 text-stone-700">Grupo Objetivo *</label>
                    <select
                      required
                      value={createLinkGroupId}
                      onChange={(e) => {
                        setCreateLinkGroupId(e.target.value);
                        setCreateLinkNodeId('');
                      }}
                      className="w-full border border-stone-300 p-2 rounded-lg bg-white"
                    >
                      <option value="">Seleccione Grupo...</option>
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name} ({g.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold mb-1 text-stone-700">
                      Rama / Nodo (Opcional)
                    </label>
                    <select
                      value={createLinkNodeId}
                      onChange={(e) => setCreateLinkNodeId(e.target.value)}
                      className="w-full border border-stone-300 p-2 rounded-lg bg-white"
                      disabled={!createLinkGroupId}
                    >
                      <option value="">Todo el Grupo (General)</option>
                      {nodes
                        .filter((n) => n.group_id === createLinkGroupId)
                        .map((n) => (
                          <option key={n.id} value={n.id}>
                            {'—'.repeat(n.depth - 1)} {n.name} ({n.code})
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1 text-stone-700">
                      Fecha Límite de Expiración *
                    </label>
                    <input
                      type="datetime-local"
                      required
                      value={createLinkExpiresAt}
                      onChange={(e) => setCreateLinkExpiresAt(e.target.value)}
                      className="w-full border border-stone-300 p-2 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold mb-1 text-stone-700">
                      Límite Máximo de Usos (Opcional)
                    </label>
                    <input
                      type="number"
                      min="1"
                      placeholder="Ilimitado si se deja vacío"
                      value={createLinkMaxUses}
                      onChange={(e) => setCreateLinkMaxUses(e.target.value)}
                      className="w-full border border-stone-300 p-2 rounded-lg"
                    />
                  </div>
                </div>

                <div className="flex justify-end space-x-2 pt-3 border-t">
                  <button
                    type="button"
                    onClick={() => setShowCreateLinkModal(false)}
                    className="px-4 py-2 border rounded-lg text-stone-600 hover:bg-stone-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={createLinkSubmitting}
                    className="px-5 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-lg font-bold shadow-sm disabled:opacity-50"
                  >
                    {createLinkSubmitting ? 'Generando Enlace...' : 'Generar Enlace Seguro'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: RECHAZO DE AUTOINSCRIPCIÓN (S2-10) */}
        {rejectModalVoter && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl border border-stone-300 shadow-2xl max-w-md w-full p-6 space-y-4">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                  <Ban className="w-5 h-5 text-seal-crimson" />
                  <span>Rechazar Solicitud de Autoinscripción</span>
                </h3>
                <button
                  onClick={() => setRejectModalVoter(null)}
                  className="text-stone-400 hover:text-stone-600 font-bold text-xl"
                >
                  &times;
                </button>
              </div>

              <p className="text-xs text-stone-600">
                Está a punto de rechazar la solicitud de <strong>{rejectModalVoter.full_name}</strong> (CI: {rejectModalVoter.document_id}).
                Indique el motivo formal del rechazo para registro en la bitácora de auditoría.
              </p>

              <div>
                <label className="block text-[11px] font-bold text-stone-700 uppercase font-mono mb-1">
                  Motivo de Rechazo *
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-stone-300 rounded-lg text-xs focus:outline-hidden focus:ring-2 focus:ring-seal-crimson"
                  placeholder="Detalle la causal reglamentaria..."
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setRejectModalVoter(null)}
                  className="px-3 py-1.5 border border-stone-300 rounded-lg text-xs font-semibold text-stone-700 hover:bg-stone-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleRejectVoter}
                  disabled={rejectSubmitting || !rejectionReason.trim()}
                  className="px-4 py-1.5 bg-seal-crimson hover:bg-seal-crimson/90 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                >
                  {rejectSubmitting ? 'Rechazando...' : 'Confirmar Rechazo'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* DRAWER: ARBITRAJE DE DUPLICADOS (IA-L2a) */}
        {selectedDuplicateIssue && (
          <DuplicateAdjudicationDrawer
            electionId={electionId || ''}
            issue={selectedDuplicateIssue}
            onClose={() => setSelectedDuplicateIssue(null)}
            onResolved={async () => {
              await Promise.all([loadBaseData(), loadVotersList()]);
            }}
          />
        )}
      </div>
    </InstitutionalShell>
  );
};
