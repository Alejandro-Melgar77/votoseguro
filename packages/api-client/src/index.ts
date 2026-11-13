/**
 * @votoseguro/api-client
 * Tipos de datos y contratos para la API de VotoSeguro v1.0
 */

export type UserRole = 'PLATFORM_ADMIN' | 'ADMIN_GENERAL' | 'ADMIN_SEGMENT' | 'OBSERVER';
export type UserStatus = 'ACTIVE' | 'LOCKED' | 'DISABLED';

export type OrganizationType = 
  | 'UNIVERSITY' 
  | 'MUNICIPALITY' 
  | 'NATIONAL' 
  | 'CORPORATE' 
  | 'COOPERATIVE' 
  | 'OTHER';

export type OrganizationStatus = 'PENDING' | 'ACTIVE' | 'SUSPENDED';

export type ElectionStatus = 
  | 'DRAFT'
  | 'SCHEDULED'
  | 'REGISTRATION_OPEN'
  | 'REGISTRATION_CLOSED'
  | 'VOTING_OPEN'
  | 'VOTING_CLOSED'
  | 'TALLIED'
  | 'CANCELLED';

export type ElectionRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface User {
  id: string;
  organization_id: string | null;
  email: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  failed_attempts: number;
  locked_until: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  org_type: OrganizationType;
  status: OrganizationStatus;
  contact_email: string;
  created_at: string;
  updated_at: string;
}

export interface ElectionRequest {
  id: string;
  organization_name: string;
  org_type: OrganizationType;
  requester_name: string;
  contact_email: string;
  contact_phone: string | null;
  desired_date: string;
  description: string | null;
  status: ElectionRequestStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  approved_organization_id: string | null;
  created_at: string;
}

export interface Election {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  timezone: string;
  registration_opens_at: string;
  registration_closes_at: string;
  voting_opens_at: string;
  voting_closes_at: string;
  status: ElectionStatus;
  k_anonymity: number;
  config_hash: string | null;
  roll_hash: string | null;
  merkle_root?: string | null;
  registration_mode?: string;
  votes_chain_head?: string | null;
  published_at: string | null;
  registration_frozen_at: string | null;
  voting_closed_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ScheduleChange {
  id: string;
  organization_id: string;
  election_id: string;
  field_name: string;
  old_value: string;
  new_value: string;
  election_status_at_change: string;
  reason: string;
  changed_by: string;
  changed_by_name?: string;
  changed_at: string;
}

export interface AdminAssignment {
  id: string;
  organization_id: string;
  user_id: string;
  election_id: string;
  group_id: string | null;
  node_id: string | null;
  permission: string;
  created_at: string;
  user?: User;
}

export interface AuditLogEntry {
  id: string;
  organization_id: string | null;
  election_id: string | null;
  actor_id: string | null;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization | null;
}

export type TokenResponse = AuthTokenResponse;

export interface ElectionCreateRequest {
  name: string;
  description?: string | null;
  timezone: string;
  registration_opens_at: string;
  registration_closes_at: string;
  voting_opens_at: string;
  voting_closes_at: string;
  k_anonymity: number;
}

export interface ScheduleUpdateRequest {
  registration_opens_at: string;
  registration_closes_at: string;
  voting_opens_at: string;
  voting_closes_at: string;
  reason?: string;
}

export interface AdminSegmentCreateRequest {
  email: string;
  full_name: string;
  password: string;
  group_id?: string | null;
  node_id?: string | null;
}

export interface OrganizationCreateRequest {
  name: string;
  slug: string;
  org_type: OrganizationType;
  contact_email: string;
  admin_user: {
    email: string;
    full_name: string;
    password: string;
  };
}

export interface ElectionRequestCreate {
  organization_name: string;
  org_type: OrganizationType;
  requester_name: string;
  contact_email: string;
  contact_phone?: string | null;
  desired_date: string;
  description?: string | null;
}

export interface ApproveElectionRequest {
  organization_slug: string;
  admin_password: string;
}

export interface RejectElectionRequest {
  rejection_reason: string;
}

// =============================================================================
// Estructura Electoral, Niveles y Nodos (S1-03)
// =============================================================================

export interface VoterGroup {
  id: string;
  organization_id: string;
  election_id: string;
  name: string;
  code: string;
  description: string | null;
  voting_opens_at: string | null;
  voting_closes_at: string | null;
  created_at: string;
  levels_count: number;
  nodes_count: number;
  contests_count: number;
}

export interface VoterGroupCreate {
  name: string;
  code: string;
  description?: string | null;
  voting_opens_at?: string | null;
  voting_closes_at?: string | null;
}

export interface VoterGroupUpdate {
  name?: string;
  code?: string;
  description?: string | null;
}

export interface VoterGroupVotingWindowUpdate {
  voting_opens_at?: string | null;
  voting_closes_at?: string | null;
}

export interface HierarchyLevel {
  id: string;
  group_id: string;
  depth: number;
  name: string;
}

export interface HierarchyLevelCreate {
  name: string;
}

export interface UnitNode {
  id: string;
  group_id: string;
  level_id: string;
  parent_id: string | null;
  name: string;
  code: string;
  path: string;
  depth: number;
  children?: UnitNode[];
}

export interface UnitNodeCreate {
  level_id: string;
  parent_id?: string | null;
  name: string;
  code: string;
}

export interface UnitNodeUpdate {
  name?: string;
  code?: string;
}

export interface NodeImportRowError {
  row: number;
  code: string;
  message: string;
}

export interface NodeImportResult {
  total_rows: number;
  created_nodes: number;
  errors: NodeImportRowError[];
}

// =============================================================================
// Filtros Dinámicos, Cargos y Circunscripciones (S1-04)
// =============================================================================

export interface FilterDefinition {
  id: string;
  group_id: string;
  key: string;
  label: string;
  allowed_values: string[];
  is_required: boolean;
}

export interface FilterDefinitionCreate {
  key: string;
  label: string;
  allowed_values: string[];
  is_required: boolean;
}

export type BreakdownKind = 'LEVEL' | 'FILTER';

export interface ContestBreakdown {
  id: string;
  contest_id: string;
  kind: BreakdownKind;
  level_id: string | null;
  filter_id: string | null;
  label: string;
}

export interface ContestBreakdownConfig {
  kind: BreakdownKind;
  level_id?: string | null;
  filter_id?: string | null;
  label: string;
}

export interface Contest {
  id: string;
  group_id: string;
  name: string;
  description: string | null;
  scope_level_id: string;
  scope_level_name?: string | null;
  scope_level_depth?: number | null;
  allow_blank: boolean;
  allow_null: boolean;
  display_order: number;
  constituencies_count: number;
  breakdowns: ContestBreakdown[];
}

export interface ContestCreate {
  name: string;
  description?: string | null;
  scope_level_id: string;
  allow_blank?: boolean;
  allow_null?: boolean;
  display_order?: number;
  breakdowns?: ContestBreakdownConfig[];
}

export interface ContestUpdate {
  name?: string;
  description?: string | null;
  scope_level_id?: string | null;
  allow_blank?: boolean;
  allow_null?: boolean;
  display_order?: number;
}

export interface Constituency {
  id: string;
  contest_id: string;
  node_id: string;
  node_name: string;
  node_code: string;
  node_path: string;
  candidates: Candidate[];
}

// =============================================================================
// Candidatos y Papeleta (S1-05)
// =============================================================================

export interface Candidate {
  id: string;
  constituency_id: string;
  name: string;
  party_or_front: string | null;
  photo_url: string | null;
  ballot_order: number;
}

export interface CandidateCreate {
  name: string;
  party_or_front?: string | null;
  photo_url?: string | null;
  ballot_order?: number | null;
}

export interface CandidateUpdate {
  name?: string;
  party_or_front?: string | null;
  photo_url?: string | null;
  ballot_order?: number | null;
}

export interface CandidateReorderRequest {
  ordered_candidate_ids: string[];
}

// =============================================================================
// Padrón Electoral, Carga Masiva y Duplicados (S1-07, IA-L2a)
// =============================================================================

export type VoterStatus = 'IMPORTED' | 'INVITED' | 'ACTIVE' | 'BLOCKED';

export interface Voter {
  id: string;
  organization_id: string;
  election_id: string;
  group_id: string;
  group_name?: string | null;
  node_id: string;
  node_name?: string | null;
  node_path?: string | null;
  document_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  attributes: Record<string, unknown>;
  status: VoterStatus;
  blocked_reason: string | null;
  invited_at: string | null;
  activated_at: string | null;
  created_at: string;
}

export interface VoterCreate {
  group_id: string;
  node_id: string;
  document_id: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  attributes?: Record<string, unknown>;
}

export interface VoterUpdate {
  email?: string | null;
  phone?: string | null;
  attributes?: Record<string, unknown>;
  status?: VoterStatus;
  blocked_reason?: string | null;
}

export interface GroupSummaryItem {
  group_id: string;
  group_name: string;
  group_code: string;
  total_voters: number;
  imported_count: number;
  invited_count: number;
  active_count: number;
  blocked_count: number;
}

export interface NodeSummaryItem {
  node_id: string;
  node_name: string;
  node_code: string;
  node_path: string;
  depth: number;
  total_voters: number;
  active_voters: number;
}

export interface RegistrationSummaryResponse {
  total_voters: number;
  imported_count: number;
  invited_count: number;
  active_count: number;
  blocked_count: number;
  activation_percentage: number;
  pending_duplicates_count: number;
  by_group: GroupSummaryItem[];
  by_node: NodeSummaryItem[];
}

export interface ImportBatch {
  id: string;
  election_id: string;
  uploaded_by: string;
  filename: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  duplicate_warnings: number;
  created_at: string;
}

export interface ImportIssue {
  id: string;
  batch_id: string;
  row_number: number;
  issue_type: 'VALIDATION_ERROR' | 'POSSIBLE_DUPLICATE';
  document_id: string | null;
  raw_full_name: string | null;
  candidate_voter_id: string | null;
  candidate_voter_name?: string | null;
  matched_voter_id: string | null;
  matched_voter_name?: string | null;
  matched_voter_document?: string | null;
  similarity_score: number | null;
  edit_distance: number | null;
  resolution: 'PENDING' | 'CONFIRMED_DISTINCT' | 'MERGED_OR_REJECTED';
  resolved_by?: string | null;
  resolved_at?: string | null;
  details: Record<string, unknown>;
  ai_verdict?: string | null;
  ai_reason?: string | null;
  ai_model?: string | null;
  ai_evaluated_at?: string | null;
}

export interface DuplicateResolveRequest {
  action: 'CONFIRM_DISTINCT' | 'BLOCK_NEW' | 'REMOVE_NEW';
  reason: string;
}

// =============================================================================
// S1-08: Enlaces de Registro y Activación Pública de Votantes
// =============================================================================

export interface RegistrationLink {
  id: string;
  election_id: string;
  group_id: string;
  node_id: string | null;
  token_hash: string;
  raw_token: string | null;
  label: string;
  expires_at: string;
  max_uses: number | null;
  uses_count: number;
  status: 'ACTIVE' | 'EXPIRED' | 'REVOKED';
  created_by: string;
  created_at: string;
  registration_url: string;
  group_name?: string | null;
  node_name?: string | null;
}

export interface CreateRegistrationLinkRequest {
  group_id: string;
  node_id?: string | null;
  label: string;
  expires_at: string;
  max_uses?: number | null;
}

export interface PublicRegistrationInfo {
  election_id: string;
  election_name: string;
  organization_name: string;
  group_name: string;
  node_name: string | null;
  node_path: string | null;
  closes_at: string;
}

export interface PublicActivationRequest {
  document_id: string;
  email?: string | null;
  phone?: string | null;
}

export interface PublicActivationResponse {
  message: string;
  voter_id: string;
  full_name: string;
  document_id: string;
  group_name: string;
  node_path: string;
  activated_at: string;
  status: string;
  credential_code?: string;
}

export interface RollHashFreezeResponse {
  message: string;
  election_id: string;
  status: string;
  roll_hash: string;
  active_voters_count: number;
  frozen_at: string;
}

// =============================================================================
// S1-09: Credenciales de Votación, Papeleta Automática y Voto Ciego
// =============================================================================

export interface VoterLoginRequest {
  document_id: string;
  credential_code: string;
}

export interface VoterSessionInfo {
  id: string;
  election_id: string;
  group_id: string;
  group_name: string;
  node_id: string;
  node_name: string;
  node_path: string;
  document_id: string;
  full_name: string;
}

export interface VoterSessionResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  voter: VoterSessionInfo;
}

export interface CandidateBallotItem {
  id: string;
  name: string;
  party_or_front?: string | null;
  photo_url?: string | null;
  ballot_order: number;
}

export interface ContestBallotItem {
  contest_id: string;
  contest_name: string;
  description?: string | null;
  scope_level_depth: number;
  scope_level_name: string;
  constituency_id: string;
  node_name: string;
  allow_blank: boolean;
  allow_null: boolean;
  candidates: CandidateBallotItem[];
}

export interface AutomaticBallotResponse {
  election_id: string;
  election_name: string;
  voter: VoterSessionInfo;
  contests: ContestBallotItem[];
}

export interface VoteSelectionItem {
  contest_id: string;
  constituency_id: string;
  choice_type: 'CANDIDATE' | 'BLANK' | 'NULL';
  candidate_id?: string | null;
}

export interface CastBallotRequest {
  votes: VoteSelectionItem[];
}

export interface CastReceiptResponse {
  receipt_hash: string;
  cast_at: string;
  election_name: string;
  votes_count: number;
  verification_url: string;
  verification_code: string;
}

export interface ReceiptChainProofItem {
  chain_index: number;
  vote_hash: string;
  prev_hash: string;
}

export interface ReceiptVerificationResponse {
  found?: boolean;
  verified?: boolean;
  receipt_hash: string;
  election_id: string;
  election_name: string;
  organization_name?: string | null;
  cast_at_minute: string;
  contests_recorded?: number;
  total_votes_in_ballot?: number;
  status: string;
  message?: string;
  chain_proof?: ReceiptChainProofItem[];
  chain_intact?: boolean;
}

export interface CredentialDispatchItem {
  voter_id: string;
  full_name: string;
  document_id: string;
  group_name: string;
  node_path: string;
  credential_code: string;
  issued_at: string;
  expires_at: string;
  is_used: boolean;
}

export interface CredentialsDispatchResponse {
  election_id: string;
  total_active_voters: number;
  credentials: CredentialDispatchItem[];
}

// =============================================================================
// S1-10: Cómputo Oficial, Desgloses Jerárquicos y k-Anonimato
// =============================================================================

export interface CandidateResultItem {
  candidate_id: string;
  full_name: string;
  ballot_number: number;
  ballot_order: number;
  party_affiliation?: string | null;
  party_color?: string | null;
  photo_url?: string | null;
  votes_count: number;
  percentage: number;
}

export interface BreakdownCellResult {
  cell_id: string;
  cell_name: string;
  cell_code?: string | null;
  cell_path?: string | null;
  total_votes: number;
  redacted_by_k_anonymity: boolean;
  k_threshold: number;
  k_anonymity_message?: string | null;
  candidates: CandidateResultItem[] | null;
  blank_count: number | null;
  null_count: number | null;
}

export interface ContestBreakdownResult {
  breakdown_id: string;
  kind: string;
  label?: string | null;
  level_id?: string | null;
  level_name?: string | null;
  filter_id?: string | null;
  filter_key?: string | null;
  cells: BreakdownCellResult[];
}

export interface ConstituencyResult {
  constituency_id: string;
  node_id: string;
  node_name: string;
  node_code: string;
  node_path: string;
  total_cast: number;
  candidates_total: number;
  blank_count: number;
  null_count: number;
  exact_match_verified: boolean;
  candidates: CandidateResultItem[];
  breakdowns: ContestBreakdownResult[];
}

export interface ContestResult {
  contest_id: string;
  contest_name: string;
  contest_code: string;
  description?: string | null;
  scope_level_id: string;
  scope_level_name: string;
  constituencies: ConstituencyResult[];
}

export interface GroupResult {
  group_id: string;
  group_name: string;
  group_code: string;
  contests: ContestResult[];
}

export interface ElectionResultsResponse {
  election_id: string;
  election_name: string;
  status: string;
  k_anonymity: number;
  published_at?: string | null;
  voting_closed_at?: string | null;
  groups: GroupResult[];
}

export interface NodeParticipationItem {
  node_id: string;
  node_name: string;
  node_code: string;
  node_path: string;
  depth: number;
  active_voters: number;
  voted_count: number;
  participation_rate_pct: number;
}

export interface GroupParticipationItem {
  group_id: string;
  group_name: string;
  group_code: string;
  active_voters: number;
  voted_count: number;
  participation_rate_pct: number;
  nodes: NodeParticipationItem[];
}

export interface ParticipationMetricsResponse {
  election_id: string;
  election_name: string;
  total_active_voters: number;
  total_voted: number;
  participation_rate_pct: number;
  by_group: GroupParticipationItem[];
}

export interface SeedDemoResponse {
  status: string;
  message: string;
  results: {
    status: string;
    org1: string;
    org2: string;
  };
}

// =============================================================================
// SPRINT 2: Integridad Criptográfica, Merkle Tree, WebSockets y Notificaciones
// =============================================================================

export interface VoteChainIntegrityResponse {
  valid: boolean;
  election_id: string;
  genesis_hash: string;
  head_hash: string | null;
  total_blocks: number;
  verified_blocks: number;
  broken_at_index: number | null;
  broken_vote_id: string | null;
  error_detail: string | null;
  checked_at: string;
}

export interface AuditChainIntegrityResponse {
  valid: boolean;
  organization_id: string | null;
  election_id: string | null;
  genesis_hash: string;
  head_hash: string | null;
  total_entries: number;
  verified_entries: number;
  broken_at_index: number | null;
  broken_entry_id: number | null;
  error_detail: string | null;
  checked_at: string;
}

export interface MerkleProofStep {
  position: 'left' | 'right';
  sibling_hash: string;
}

export interface MerkleInclusionProofResponse {
  election_id: string;
  document_id: string;
  leaf_hash: string;
  leaf_index: number;
  total_active_voters: number;
  merkle_root: string;
  proof: MerkleProofStep[];
  is_frozen?: boolean;
}

export interface MerkleVerifyRequest {
  leaf_hash: string;
  merkle_root: string;
  proof: MerkleProofStep[];
}

export interface MerkleVerifyResponse {
  valid: boolean;
  computed_root: string;
  expected_root: string;
  is_valid?: boolean;
  calculated_root?: string;
}

export interface RegistrationMetricsDTO {
  imported: number;
  invited: number;
  active: number;
  blocked: number;
  pending_approval: number;
  total: number;
  activation_rate_pct: number;
}

export interface ParticipationMetricsDTO {
  total_eligible_active: number;
  total_voted: number;
  abstention_count: number;
  participation_rate_pct: number;
}

export interface SegmentBreakdownItemDTO {
  group_id: string;
  group_name: string;
  node_id: string;
  node_name: string;
  node_path: string;
  active_voters: number;
  votes_cast: number;
  participation_pct: number;
}

export interface HourlyVotesBucketDTO {
  hour_bucket_utc: string;
  hour_label_local: string;
  ballots_cast: number;
  cumulative_ballots: number;
}

export interface LiveDashboardSnapshot {
  election_id: string;
  election_name: string;
  status: string;
  server_now_utc: string;
  config_hash: string | null;
  roll_hash: string | null;
  merkle_root: string | null;
  registration_metrics: RegistrationMetricsDTO;
  participation_metrics: ParticipationMetricsDTO;
  segment_breakdown: SegmentBreakdownItemDTO[];
  hourly_votes_series: HourlyVotesBucketDTO[];
}

export interface SelfRegistrationNodeDTO {
  id: string;
  name: string;
  code: string;
  path: string;
  depth: number;
}

export interface SelfRegistrationGroupDTO {
  id: string;
  name: string;
  code: string;
  nodes: SelfRegistrationNodeDTO[];
}

export interface SelfRegistrationInfoResponse {
  election_id: string;
  election_name: string;
  registration_mode: string;
  status: string;
  is_open: boolean;
  groups: SelfRegistrationGroupDTO[];
  filter_definitions: Record<string, any>[];
}

export interface SelfRegistrationRequest {
  document_id: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  group_id: string;
  node_id: string;
  attributes?: Record<string, any>;
}

export interface SelfRegistrationResponse {
  success: boolean;
  message: string;
  voter_id: string;
  document_id: string;
  full_name: string;
  status: string;
}

export interface NotificationOutboxItem {
  id: string;
  organization_id: string;
  election_id: string;
  schedule_change_id: string | null;
  recipient_email: string;
  recipient_name: string;
  subject: string;
  body_text: string;
  delivery_status: 'SENT_SMTP' | 'STORED_DEMO_OUTBOX' | 'FAILED';
  created_at: string;
}

export interface PaillierBenchmarkResponse {
  key_size_bits: number;
  keygen_duration_ms: number;
  simulated_ballots_count: number;
  encryption_duration_ms: number;
  homomorphic_addition_duration_ms: number;
  final_decryption_duration_ms: number;
  total_benchmark_duration_ms: number;
  sample_ciphertext_preview: string | null;
  mathematical_equivalence_verified: boolean;
  decrypted_tallies: Record<string, Record<string, number[]>>;
  verification_cells: Array<{
    constituency_id: string;
    segment_path: string;
    expected_plaintext_tally: number[];
    decrypted_homomorphic_tally: number[];
    is_exact_match: boolean;
  }>;
}

// ==========================================
// Contratos de IA Local (LFM3-1.7B) - Sprint 2
// ==========================================

export interface AnomalyExplanationResponse {
  anomaly_id: string;
  code: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  metrics_summary: Record<string, any>;
  explanation_es: string;
  recommended_checks: string[];
  requires_human_decision: boolean;
  ai_source: 'LFM3-1.7B' | 'LFM3-1.7B_NEURAL_TUNNEL' | 'DETERMINISTIC_FALLBACK' | string;
  model_name?: string;
  latency_ms?: number;
}

export interface AnomalyScanResponse {
  election_id: string;
  election_status: string;
  total_active_voters: number;
  total_ballots_cast: number;
  participation_rate_pct: number;
  anomalies_found_count: number;
  anomalies: AnomalyExplanationResponse[];
  scanned_at_utc: string;
  is_simulation: boolean;
}

export interface DuplicateAdjudicationSuggestion {
  issue_id?: string;
  verdict: 'mismo' | 'distinto' | 'dudoso';
  confidence_label: 'ALTA' | 'MEDIA' | 'BAJA';
  short_reason: string;
  human_action_required: boolean;
  ai_source: 'LFM3-1.7B' | 'LFM3-1.7B_NEURAL_TUNNEL' | 'DETERMINISTIC_FALLBACK' | string;
  model_name?: string;
  latency_ms?: number;
}

export interface BatchDuplicateAdjudicationResponse {
  batch_id: string;
  total_evaluated: number;
  suggestions: DuplicateAdjudicationSuggestion[];
  adjudicated_at: string;
}

export interface IdCardExtractionRequest {
  raw_ocr_text: string;
  election_id?: string | null;
}

export interface IdCardExtractionResponse {
  ci: string;
  nombres: string;
  apellidos: string;
  fecha_nacimiento: string | null;
  regex_valid: boolean;
  confidence_note: string;
  requires_voter_confirmation: boolean;
  ai_source: 'LFM3-1.7B' | 'LFM3-1.7B_NEURAL_TUNNEL' | 'DETERMINISTIC_FALLBACK' | string;
  model_name?: string;
  latency_ms?: number;
}

export interface DocumentCitation {
  doc_id: string;
  title: string;
  excerpt: string;
  section?: string;
}

export interface RagAssistantRequest {
  question: string;
  context_role?: 'VOTER' | 'ADMIN' | 'PUBLIC';
  election_id?: string | null;
}

export type AssistantQuestionRequest = RagAssistantRequest;

export interface RagAssistantResponse {
  question: string;
  answer: string;
  answered_from_docs: boolean;
  citations: DocumentCitation[];
  escalate_to_support: boolean;
  ai_source: 'LFM3-1.7B' | 'LFM3-1.7B_NEURAL_TUNNEL' | 'DETERMINISTIC_FALLBACK' | string;
  model_name?: string;
  latency_ms?: number;
  sources?: DocumentCitation[];
  suggests_support?: boolean;
  source?: string;
}

export type AssistantAnswerResponse = RagAssistantResponse;

export interface AiNodeStatusResponse {
  status: 'CONNECTED' | 'DISCONNECTED' | string;
  is_online: boolean;
  llm_base_url: string;
  llm_model_name: string;
  provider: string;
  strict_neural_mode: boolean;
  timeout_seconds: number;
  last_ping_status: string | null;
  last_ping_latency_ms: number | null;
  last_ping_at: string | null;
  available_models: string[];
  message: string;
}

export interface AiNodeConfigUpdateRequest {
  llm_base_url?: string;
  llm_model_name?: string;
  provider?: string;
  strict_neural_mode?: boolean;
  timeout_seconds?: number;
}

export interface AiNodeTestInferenceRequest {
  prompt?: string;
}

export interface AiNodeTestInferenceResponse {
  success: boolean;
  ai_source: string;
  model_name: string;
  latency_ms: number;
  output_text: string;
  parsed_json: Record<string, any> | null;
  error?: string | null;
}

export interface AiNodePingRequest {
  node_name?: string;
  ngrok_url?: string;
  model_name?: string;
}

export interface AiNodePingResponse {
  acknowledged: boolean;
  node_status: string;
  message: string;
}

export type VoiceBallotAction =
  | 'READ_BALLOT'
  | 'NEXT_CONTEST'
  | 'PREV_CONTEST'
  | 'PREVIOUS_CONTEST'
  | 'SELECT_CANDIDATE'
  | 'SELECT_BLANK'
  | 'SELECT_NULL'
  | 'READ_SUMMARY'
  | 'PREPARE_CAST'
  | 'CONFIRM_CAST'
  | 'CANCEL'
  | 'CANCEL_SELECTION'
  | 'HELP'
  | 'UNKNOWN';

export interface VoiceBallotCommand {
  action: VoiceBallotAction;
  candidateNumber?: number;
  rawTranscript: string;
  feedbackMessage: string;
}



