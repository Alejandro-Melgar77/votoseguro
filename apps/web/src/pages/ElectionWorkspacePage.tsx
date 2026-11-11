import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Vote,
  Plus,
  CalendarDays,
  Users,
  ShieldCheck,
  Clock,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import type { Election, ElectionCreateRequest } from '@votoseguro/api-client';
import { formatElectoralDateTime } from '@/lib/timezone';

export const ElectionWorkspacePage: React.FC = () => {
  const { organization, isAdminGeneral } = useAuth();
  const [elections, setElections] = useState<Election[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal para nueva elección
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<ElectionCreateRequest>({
    name: '',
    description: '',
    timezone: 'America/La_Paz',
    registration_opens_at: new Date(Date.now() + 86400000).toISOString(),
    registration_closes_at: new Date(Date.now() + 5 * 86400000).toISOString(),
    voting_opens_at: new Date(Date.now() + 6 * 86400000).toISOString(),
    voting_closes_at: new Date(Date.now() + 7 * 86400000).toISOString(),
    k_anonymity: 5,
  });

  const loadElections = async () => {
    setIsLoading(true);
    try {
      const data = await api.get<Election[]>('/elections');
      setElections(data);
    } catch (err: any) {
      setError(err.message || 'Error al cargar las elecciones.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadElections();
  }, []);

  const handleCreateElection = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/elections', form);
      setIsModalOpen(false);
      await loadElections();
    } catch (err: any) {
      alert(err.message || 'Error al crear la elección.');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DRAFT':
        return 'bg-stone-100 text-stone-700 border-stone-300';
      case 'SCHEDULED':
        return 'bg-amber-100 text-seal-amber border-amber-300';
      case 'REGISTRATION_OPEN':
      case 'VOTING_OPEN':
        return 'bg-emerald-100 text-seal-emerald border-emerald-300';
      case 'REGISTRATION_CLOSED':
        return 'bg-civic-navy-900 text-stone-100 border-civic-navy-800';
      case 'VOTING_CLOSED':
      case 'TALLIED':
        return 'bg-stone-200 text-civic-navy-900 border-stone-400';
      default:
        return 'bg-red-100 text-seal-crimson border-red-300';
    }
  };

  return (
    <InstitutionalShell>
      <div className="space-y-6">
        {/* Cabecera de Elecciones */}
        <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="font-title text-xl font-bold text-civic-navy-900">
              Procesos Electorales — {organization?.name}
            </h2>
            <p className="text-xs text-stone-500 mt-1">
              Gestión y supervisión de elecciones institucionales, cronogramas y delegaciones de auditoría.
            </p>
          </div>
          {isAdminGeneral && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white font-semibold text-xs rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Nueva Elección</span>
            </button>
          )}
        </div>

        {error && (
          <div className="p-4 bg-seal-crimson-light border border-seal-crimson text-seal-crimson-dark text-xs rounded-xl flex items-start space-x-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Listado de Elecciones */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {elections.map((election) => (
            <div
              key={election.id}
              className="bg-white border border-stone-300 rounded-xl p-6 shadow-electoral hover:border-civic-navy-800 transition-all flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border font-mono ${getStatusColor(
                      election.status
                    )}`}
                  >
                    {election.status}
                  </span>
                  <span className="text-[11px] font-mono text-stone-400">
                    k={election.k_anonymity}
                  </span>
                </div>

                <h3 className="font-title text-base font-bold text-civic-navy-900">
                  {election.name}
                </h3>
                {election.description && (
                  <p className="text-xs text-stone-500 line-clamp-2">{election.description}</p>
                )}

                <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 text-[11px] font-mono space-y-1">
                  <div className="flex justify-between text-stone-600">
                    <span>Registro:</span>
                    <span className="font-bold text-stone-800">
                      {formatElectoralDateTime(election.registration_opens_at, election.timezone)}
                    </span>
                  </div>
                  <div className="flex justify-between text-stone-600">
                    <span>Votación:</span>
                    <span className="font-bold text-seal-emerald">
                      {formatElectoralDateTime(election.voting_opens_at, election.timezone)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Botones de acción */}
              <div className="pt-4 mt-4 border-t border-stone-200 flex items-center justify-between">
                <Link
                  to={`/elections/${election.id}/delegates`}
                  className="text-xs font-semibold text-stone-600 hover:text-civic-navy-900 flex items-center space-x-1"
                >
                  <Users className="w-3.5 h-3.5" />
                  <span>Delegados</span>
                </Link>

                <Link
                  to={`/elections/${election.id}/schedule`}
                  className="px-3.5 py-1.5 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-sm"
                >
                  <CalendarDays className="w-3.5 h-3.5 text-seal-amber" />
                  <span>Control de Cronograma</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                </Link>
              </div>
            </div>
          ))}

          {elections.length === 0 && !isLoading && (
            <div className="col-span-full bg-white border border-stone-300 rounded-xl p-12 text-center text-stone-400 shadow-sm">
              <Vote className="w-12 h-12 text-stone-300 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-stone-700">No hay procesos electorales creados</h4>
              <p className="text-xs text-stone-400 mt-1">
                Comience creando la primera elección de su institución mediante el botón superior.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Crear Elección */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-xl border border-stone-300 shadow-2xl max-w-xl w-full p-6 space-y-4 my-8">
            <h3 className="font-title text-base font-bold text-civic-navy-900 border-b pb-2">
              Configurar Nuevo Proceso Electoral
            </h3>
            <form onSubmit={handleCreateElection} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Nombre de la Elección</label>
                <input
                  type="text"
                  required
                  placeholder="Ej. Elección de Rectorado y Decanaturas 2026"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">Descripción (Opcional)</label>
                <textarea
                  rows={2}
                  value={form.description || ''}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full border p-2 rounded"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Zona Horaria (IANA)</label>
                  <input
                    type="text"
                    required
                    value={form.timezone}
                    onChange={(e) => setForm({ ...form, timezone: e.target.value })}
                    className="w-full border p-2 rounded font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">k-Anonimato (Mínimo de votos)</label>
                  <input
                    type="number"
                    min={0}
                    value={form.k_anonymity}
                    onChange={(e) => setForm({ ...form, k_anonymity: parseInt(e.target.value) || 0 })}
                    className="w-full border p-2 rounded font-mono"
                  />
                </div>
              </div>

              <div className="pt-2 border-t space-y-3">
                <span className="font-mono text-[10px] text-stone-500 uppercase font-bold block">
                  Cronograma Inicial Obligatorio (Invariable: Reg_Open &lt; Reg_Close ≤ Vote_Open &lt; Vote_Close)
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold mb-1">Inicio de Registro</label>
                    <input
                      type="datetime-local"
                      required
                      onChange={(e) =>
                        setForm({ ...form, registration_opens_at: new Date(e.target.value).toISOString() })
                      }
                      className="w-full border p-2 rounded font-mono text-[11px]"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold mb-1">Fin de Registro</label>
                    <input
                      type="datetime-local"
                      required
                      onChange={(e) =>
                        setForm({ ...form, registration_closes_at: new Date(e.target.value).toISOString() })
                      }
                      className="w-full border p-2 rounded font-mono text-[11px]"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold mb-1">Inicio de Votación</label>
                    <input
                      type="datetime-local"
                      required
                      onChange={(e) =>
                        setForm({ ...form, voting_opens_at: new Date(e.target.value).toISOString() })
                      }
                      className="w-full border p-2 rounded font-mono text-[11px]"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold mb-1">Fin de Votación</label>
                    <input
                      type="datetime-local"
                      required
                      onChange={(e) =>
                        setForm({ ...form, voting_closes_at: new Date(e.target.value).toISOString() })
                      }
                      className="w-full border p-2 rounded font-mono text-[11px]"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
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
                  Guardar Elección
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </InstitutionalShell>
  );
};
