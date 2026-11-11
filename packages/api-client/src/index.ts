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

