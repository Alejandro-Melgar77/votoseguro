import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Users, Plus, Trash2, ArrowLeft, Shield, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import type { AdminAssignment, AdminSegmentCreateRequest, Election } from '@votoseguro/api-client';
import { formatElectoralDateTime } from '@/lib/timezone';

export const DelegateAdminsPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();
  const { isAdminGeneral } = useAuth();

  const [election, setElection] = useState<Election | null>(null);
  const [delegates, setDelegates] = useState<AdminAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal para nuevo delegado
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<AdminSegmentCreateRequest>({
    email: '',
    full_name: '',
    password: '',
  });

  const loadData = async () => {
    if (!electionId) return;
    setIsLoading(true);
    try {
      const [electionData, delegatesData] = await Promise.all([
        api.get<Election>(`/elections/${electionId}`),
        api.get<AdminAssignment[]>(`/elections/${electionId}/delegates`),
      ]);
      setElection(electionData);
      setDelegates(delegatesData);
    } catch (err: any) {
      setError(err.message || 'Error al cargar los delegados de la elección.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [electionId]);

  const handleCreateDelegate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!electionId) return;
    try {
      await api.post(`/elections/${electionId}/delegates`, form);
      setIsModalOpen(false);
      setForm({ email: '', full_name: '', password: '' });
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error al asignar delegado.');
    }
  };

  const handleRevoke = async (assignmentId: string) => {
    if (!electionId) return;
    if (!confirm('¿Confirma la revocación de permisos a este administrador delegado?')) {
      return;
    }
    try {
      await api.delete(`/elections/${electionId}/delegates/${assignmentId}`);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error al revocar delegado.');
    }
  };

  return (
    <InstitutionalShell activeElectionId={electionId} timezone={election?.timezone}>
      <div className="space-y-6">
        {/* Navegación y Cabecera */}
        <div className="flex items-center justify-between">
          <Link
            to="/workspace"
            className="text-xs font-semibold text-stone-500 hover:text-civic-navy-900 flex items-center space-x-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Volver a Elecciones</span>
          </Link>
        </div>

        <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-amber-700 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded">
                DELEGADOS DE AUDITORÍA (S1-11)
              </span>
              <span className="text-xs font-mono text-stone-400">Elección: {election?.name}</span>
            </div>
            <h2 className="font-title text-xl font-bold text-civic-navy-900 mt-1">
              Supervisores y Administradores de Segmento (Solo Lectura)
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Los usuarios con rol ADMIN_SEGMENT pueden monitorear el padrón y los resultados de su segmento, con restricción estricta de modificación.
            </p>
          </div>

          {isAdminGeneral && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white font-semibold text-xs rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Asignar Delegado</span>
            </button>
          )}
        </div>

        {error && (
          <div className="p-4 bg-seal-crimson-light border border-seal-crimson text-seal-crimson-dark text-xs rounded-xl flex items-start space-x-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Tabla de Delegados */}
        <div className="bg-white border border-stone-300 rounded-xl shadow-electoral overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-civic-navy-900 text-stone-300 uppercase font-mono text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">Usuario / Delegado</th>
                  <th className="py-3 px-4">Correo</th>
                  <th className="py-3 px-4">Permiso</th>
                  <th className="py-3 px-4">Alcance Asignado</th>
                  <th className="py-3 px-4">Fecha Asignación</th>
                  {isAdminGeneral && <th className="py-3 px-4 text-right">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200">
                {delegates.map((item) => (
                  <tr key={item.id} className="hover:bg-stone-50 transition-colors">
                    <td className="py-3 px-4 font-semibold text-civic-navy-900">
                      {item.user?.full_name || 'Usuario'}
                    </td>
                    <td className="py-3 px-4 text-stone-600 font-mono text-[11px]">
                      {item.user?.email || '—'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-seal-amber">
                        SOLO LECTURA ({item.permission})
                      </span>
                    </td>
                    <td className="py-3 px-4 text-stone-600 font-mono text-[11px]">
                      {item.node_id ? `Nodo: ${item.node_id}` : item.group_id ? `Grupo: ${item.group_id}` : 'Toda la elección'}
                    </td>
                    <td className="py-3 px-4 font-mono text-stone-500 text-[11px]">
                      {formatElectoralDateTime(item.created_at, election?.timezone)}
                    </td>
                    {isAdminGeneral && (
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleRevoke(item.id)}
                          className="p-1 hover:bg-red-50 text-seal-crimson rounded transition-colors"
                          title="Revocar asignación"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {delegates.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-stone-400">
                      No hay delegados asignados a esta elección.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modal: Asignar Delegado */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl border border-stone-300 shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-title text-base font-bold text-civic-navy-900 border-b pb-2">
              Asignar Administrador Delegado (ADMIN_SEGMENT)
            </h3>
            <p className="text-xs text-stone-600">
              Crea o vincula una cuenta con permisos exclusivos de solo lectura para la supervisión de este proceso.
            </p>
            <form onSubmit={handleCreateDelegate} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Nombre Completo del Delegado</label>
                <input
                  type="text"
                  required
                  placeholder="Ej. Ing. Juan Pérez"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">Correo Electrónico Institucional</label>
                <input
                  type="email"
                  required
                  placeholder="delegado@institucion.edu"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">Contraseña de Acceso</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Mínimo 8 caracteres"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full border p-2 rounded"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 border rounded text-stone-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-civic-navy-900 text-white rounded font-semibold"
                >
                  Asignar Delegado
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </InstitutionalShell>
  );
};
