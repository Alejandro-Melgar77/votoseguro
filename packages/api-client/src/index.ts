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
}

export interface DuplicateResolveRequest {
  action: 'CONFIRM_DISTINCT' | 'BLOCK_NEW' | 'REMOVE_NEW';
  reason: string;
}


