import React, { useEffect, useState } from 'react';
import {
  Building2,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  FileText,
  AlertCircle,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import type {
  Organization,
  ElectionRequest,
  OrganizationCreateRequest,
  ApproveElectionRequest,
  RejectElectionRequest,
} from '@votoseguro/api-client';
import { formatElectoralDateTime } from '@/lib/timezone';
import { LocalAiNodeBridgePanel } from '@/components/electoral/LocalAiNodeBridgePanel';

export const PlatformAdminConsolePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'orgs' | 'requests'>('orgs');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [requests, setRequests] = useState<ElectionRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modales
  const [isNewOrgModalOpen, setIsNewOrgModalOpen] = useState(false);
  const [approvingRequest, setApprovingRequest] = useState<ElectionRequest | null>(null);
  const [rejectingRequest, setRejectingRequest] = useState<ElectionRequest | null>(null);

  // Estados de formularios
  const [newOrgForm, setNewOrgForm] = useState<OrganizationCreateRequest>({
    name: '',
    slug: '',
    org_type: 'UNIVERSITY',
    contact_email: '',
    admin_user: {
      email: '',
      full_name: '',
      password: '',
    },
  });

  const [approveForm, setApproveForm] = useState<ApproveElectionRequest>({
    organization_slug: '',
    admin_password: '',
  });

  const [rejectReason, setRejectReason] = useState('');
  const [isSeedingDemo, setIsSeedingDemo] = useState(false);
  const [seedFeedback, setSeedFeedback] = useState<string | null>(null);

  const handleTriggerSeedDemo = async () => {
    if (
      !window.confirm(
        '¿Desea aprovisionar los datos de demostración de Universidad EL GRAN ESTUDIO y Elecciones Nacionales Ecuador (seed:demo)?'
      )
    ) {
      return;
    }
    try {
      setIsSeedingDemo(true);
      setSeedFeedback(null);
      const res = await api.post<{
        status: string;
        message: string;
        results: { org1: string; org2: string };
      }>('/platform/seed-demo');
      setSeedFeedback(
        `Datos de demostración aprovisionados exitosamente: ${res.results.org1} y ${res.results.org2}.`
      );
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error al ejecutar el sembrado de demostración.');
    } finally {
      setIsSeedingDemo(false);
    }
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [orgsData, reqsData] = await Promise.all([
        api.get<Organization[]>('/platform/organizations'),
        api.get<ElectionRequest[]>('/platform/election-requests'),
      ]);
      setOrganizations(orgsData);
      setRequests(reqsData);
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos de plataforma.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/platform/organizations', newOrgForm);
      setIsNewOrgModalOpen(false);
      setNewOrgForm({
        name: '',
        slug: '',
        org_type: 'UNIVERSITY',
        contact_email: '',
        admin_user: { email: '', full_name: '', password: '' },
      });
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error al crear la organización.');
    }
  };

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!approvingRequest) return;
    try {
      await api.post(`/platform/election-requests/${approvingRequest.id}/approve`, approveForm);
      setApprovingRequest(null);
      setApproveForm({ organization_slug: '', admin_password: '' });
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error al aprobar solicitud.');
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingRequest) return;
    try {
      await api.post(`/platform/election-requests/${rejectingRequest.id}/reject`, {
        rejection_reason: rejectReason,
      });
      setRejectingRequest(null);
      setRejectReason('');
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error al rechazar solicitud.');
    }
  };

  return (
    <InstitutionalShell>
      <div className="space-y-6">
        {/* Cabecera de la Consola */}
        <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="font-title text-xl font-bold text-civic-navy-900">
              Consola del Operador Central de Plataforma (PLATFORM_ADMIN)
            </h2>
            <p className="text-xs text-stone-500 mt-1">
              Aprovisionamiento de organizaciones multi-tenant y revisión de solicitudes de elección.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleTriggerSeedDemo}
              disabled={isSeedingDemo}
              className="px-3.5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isSeedingDemo ? 'Aprovisionando...' : 'Sembrar Datos Demo (seed:demo)'}</span>
            </button>
            <button
              onClick={() => setIsNewOrgModalOpen(true)}
              className="px-4 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white font-semibold text-xs rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Nueva Organización</span>
            </button>
          </div>
        </div>

        {seedFeedback && (
          <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg text-xs text-emerald-900 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{seedFeedback}</span>
          </div>
        )}

        {/* Panel del Puente Neuronal Local (Sprint 2.5) */}
        <LocalAiNodeBridgePanel defaultExpanded={false} />

        {/* Selector de Pestañas */}
        <div className="flex border-b border-stone-300 space-x-6 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('orgs')}
            className={`pb-3 transition-colors flex items-center space-x-2 border-b-2 ${
              activeTab === 'orgs'
                ? 'border-civic-navy-900 text-civic-navy-900 font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>Organizaciones Activas ({organizations.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`pb-3 transition-colors flex items-center space-x-2 border-b-2 ${
              activeTab === 'requests'
                ? 'border-civic-navy-900 text-civic-navy-900 font-bold'
                : 'border-transparent text-stone-500 hover:text-stone-800'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>
              Solicitudes Públicas de Elección (
              {requests.filter((r) => r.status === 'PENDING').length} pendientes)
            </span>
          </button>
        </div>

        {/* Tab 1: Organizaciones */}
        {activeTab === 'orgs' && (
          <div className="bg-white border border-stone-300 rounded-xl shadow-electoral overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-civic-navy-900 text-stone-300 uppercase font-mono text-[10px] tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Institución</th>
                    <th className="py-3 px-4">Slug / Tenant</th>
                    <th className="py-3 px-4">Tipo</th>
                    <th className="py-3 px-4">Contacto</th>
                    <th className="py-3 px-4">Estado</th>
                    <th className="py-3 px-4">Fecha Creación</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200">
                  {organizations.map((org) => (
                    <tr key={org.id} className="hover:bg-stone-50 transition-colors">
                      <td className="py-3 px-4 font-semibold text-civic-navy-900">{org.name}</td>
                      <td className="py-3 px-4 font-mono text-stone-600">{org.slug}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-stone-500">
                        {org.org_type}
                      </td>
                      <td className="py-3 px-4 text-stone-600">{org.contact_email}</td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-seal-emerald">
                          {org.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-stone-500 text-[11px]">
                        {formatElectoralDateTime(org.created_at)}
                      </td>
                    </tr>
                  ))}
                  {organizations.length === 0 && !isLoading && (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-stone-400">
                        No hay organizaciones creadas todavía.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Solicitudes Públicas */}
        {activeTab === 'requests' && (
          <div className="bg-white border border-stone-300 rounded-xl shadow-electoral overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-civic-navy-900 text-stone-300 uppercase font-mono text-[10px] tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Institución Solicitante</th>
                    <th className="py-3 px-4">Representante</th>
                    <th className="py-3 px-4">Contacto</th>
                    <th className="py-3 px-4">Fecha Deseada</th>
                    <th className="py-3 px-4">Estado</th>
                    <th className="py-3 px-4 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200">
                  {requests.map((req) => (
                    <tr key={req.id} className="hover:bg-stone-50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-civic-navy-900">
                          {req.organization_name}
                        </div>
                        <div className="text-[10px] font-mono text-stone-500">{req.org_type}</div>
                      </td>
                      <td className="py-3 px-4 text-stone-700">{req.requester_name}</td>
                      <td className="py-3 px-4">
                        <div className="text-stone-700">{req.contact_email}</div>
                        {req.contact_phone && (
                          <div className="text-[11px] text-stone-400">{req.contact_phone}</div>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-stone-600">
                        {formatElectoralDateTime(req.desired_date)}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                            req.status === 'PENDING'
                              ? 'bg-amber-100 text-seal-amber'
                              : req.status === 'APPROVED'
                              ? 'bg-emerald-100 text-seal-emerald'
                              : 'bg-red-100 text-seal-crimson'
                          }`}
                        >
                          {req.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        {req.status === 'PENDING' ? (
                          <>
                            <button
                              onClick={() => {
                                setApprovingRequest(req);
                                setApproveForm({
                                  organization_slug: req.organization_name
                                    .toLowerCase()
                                    .replace(/[^a-z0-9]/g, '-')
                                    .replace(/-+/g, '-')
                                    .replace(/^-|-$/g, ''),
                                  admin_password: '',
                                });
                              }}
                              className="px-2.5 py-1 bg-seal-emerald hover:bg-emerald-700 text-white rounded text-[11px] font-semibold transition-colors"
                            >
                              Aprobar
                            </button>
                            <button
                              onClick={() => {
                                setRejectingRequest(req);
                                setRejectReason('');
                              }}
                              className="px-2.5 py-1 bg-stone-100 hover:bg-red-50 text-seal-crimson border border-stone-300 rounded text-[11px] font-semibold transition-colors"
                            >
                              Rechazar
                            </button>
                          </>
                        ) : (
                          <span className="text-[11px] text-stone-400 italic">Revisada</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {requests.length === 0 && !isLoading && (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-stone-400">
                        No hay solicitudes de elección registradas.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Modal: Crear Nueva Organización Manualmente */}
      {isNewOrgModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl border border-stone-300 shadow-2xl max-w-lg w-full overflow-hidden p-6 space-y-4">
            <h3 className="font-title text-base font-bold text-civic-navy-900 border-b pb-2">
              Nueva Organización Tenant + Administrador General
            </h3>
            <form onSubmit={handleCreateOrg} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Nombre de la Institución</label>
                <input
                  type="text"
                  required
                  value={newOrgForm.name}
                  onChange={(e) => setNewOrgForm({ ...newOrgForm, name: e.target.value })}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Slug (Identificador URL)</label>
                  <input
                    type="text"
                    required
                    value={newOrgForm.slug}
                    onChange={(e) => setNewOrgForm({ ...newOrgForm, slug: e.target.value })}
                    className="w-full border p-2 rounded font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Tipo</label>
                  <select
                    value={newOrgForm.org_type}
                    onChange={(e) =>
                      setNewOrgForm({ ...newOrgForm, org_type: e.target.value as any })
                    }
                    className="w-full border p-2 rounded"
                  >
                    <option value="UNIVERSITY">Universidad</option>
                    <option value="MUNICIPALITY">Municipio</option>
                    <option value="NATIONAL">Nacional</option>
                    <option value="CORPORATE">Colegio/Empresa</option>
                    <option value="OTHER">Otro</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block font-semibold mb-1">Email de Contacto Institucional</label>
                <input
                  type="email"
                  required
                  value={newOrgForm.contact_email}
                  onChange={(e) =>
                    setNewOrgForm({ ...newOrgForm, contact_email: e.target.value })
                  }
                  className="w-full border p-2 rounded"
                />
              </div>

              <div className="pt-2 border-t space-y-3">
                <span className="font-mono text-[10px] text-stone-500 uppercase font-bold block">
                  Primer Usuario Administrador General
                </span>
                <div>
                  <label className="block font-semibold mb-1">Nombre Completo</label>
                  <input
                    type="text"
                    required
                    value={newOrgForm.admin_user.full_name}
                    onChange={(e) =>
                      setNewOrgForm({
                        ...newOrgForm,
                        admin_user: { ...newOrgForm.admin_user, full_name: e.target.value },
                      })
                    }
                    className="w-full border p-2 rounded"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1">Correo de Acceso</label>
                    <input
                      type="email"
                      required
                      value={newOrgForm.admin_user.email}
                      onChange={(e) =>
                        setNewOrgForm({
                          ...newOrgForm,
                          admin_user: { ...newOrgForm.admin_user, email: e.target.value },
                        })
                      }
                      className="w-full border p-2 rounded"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold mb-1">Contraseña Inicial</label>
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={newOrgForm.admin_user.password}
                      onChange={(e) =>
                        setNewOrgForm({
                          ...newOrgForm,
                          admin_user: { ...newOrgForm.admin_user, password: e.target.value },
                        })
                      }
                      className="w-full border p-2 rounded"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <button
                  type="button"
                  onClick={() => setIsNewOrgModalOpen(false)}
                  className="px-3 py-1.5 border rounded text-stone-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-civic-navy-900 text-white rounded font-semibold"
                >
                  Crear Organización
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Aprobar Solicitud */}
      {approvingRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl border border-stone-300 shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-title text-base font-bold text-civic-navy-900 border-b pb-2">
              Aprobar Solicitud Elector: {approvingRequest.organization_name}
            </h3>
            <p className="text-xs text-stone-600">
              Se creará la institución y se asignará a{' '}
              <span className="font-semibold">{approvingRequest.requester_name}</span> como ADMIN_GENERAL.
            </p>
            <form onSubmit={handleApprove} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Slug Institucional</label>
                <input
                  type="text"
                  required
                  value={approveForm.organization_slug}
                  onChange={(e) =>
                    setApproveForm({ ...approveForm, organization_slug: e.target.value })
                  }
                  className="w-full border p-2 rounded font-mono"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">
                  Contraseña Temporal para el Administrador
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Mínimo 8 caracteres"
                  value={approveForm.admin_password}
                  onChange={(e) =>
                    setApproveForm({ ...approveForm, admin_password: e.target.value })
                  }
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setApprovingRequest(null)}
                  className="px-3 py-1.5 border rounded text-stone-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-seal-emerald text-white rounded font-semibold"
                >
                  Confirmar Aprobación
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Rechazar Solicitud */}
      {rejectingRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl border border-stone-300 shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-title text-base font-bold text-seal-crimson border-b pb-2">
              Rechazar Solicitud: {rejectingRequest.organization_name}
            </h3>
            <form onSubmit={handleReject} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Motivo Formal de Rechazo</label>
                <textarea
                  required
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Detalle el motivo por el cual la solicitud es denegada..."
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setRejectingRequest(null)}
                  className="px-3 py-1.5 border rounded text-stone-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-seal-crimson text-white rounded font-semibold"
                >
                  Confirmar Rechazo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </InstitutionalShell>
  );
};
