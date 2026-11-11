import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Election,
  VoterGroup,
  HierarchyLevel,
  UnitNode,
  Contest,
  FilterDefinition,
} from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { CryptographicHashBadge } from '@/components/electoral/CryptographicHashBadge';
import { HierarchyTreeExplorer } from '@/components/electoral/HierarchyTreeExplorer';
import { PublicationCeremonyModal } from '@/components/electoral/PublicationCeremonyModal';

export const StructureArchitectPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();

  const [election, setElection] = useState<Election | null>(null);
  const [groups, setGroups] = useState<VoterGroup[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  const [levels, setLevels] = useState<HierarchyLevel[]>([]);
  const [nodes, setNodes] = useState<UnitNode[]>([]);
  const [contests, setContests] = useState<Contest[]>([]);
  const [filters, setFilters] = useState<FilterDefinition[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modales
  const [showNewGroupModal, setShowNewGroupModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupCode, setNewGroupCode] = useState('');
  const [showNewLevelModal, setShowNewLevelModal] = useState(false);
  const [newLevelName, setNewLevelName] = useState('');
  const [showNewContestModal, setShowNewContestModal] = useState(false);
  const [contestName, setContestName] = useState('');
  const [contestScopeId, setContestScopeId] = useState('');
  const [contestAllowBlank, setContestAllowBlank] = useState(true);
  const [contestAllowNull, setContestAllowNull] = useState(true);
  const [showNewFilterModal, setShowNewFilterModal] = useState(false);
  const [filterKey, setFilterKey] = useState('');
  const [filterLabel, setFilterLabel] = useState('');
  const [filterValues, setFilterValues] = useState('');
  const [filterRequired, setFilterRequired] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);

  const isDraft = election?.status === 'DRAFT';

  const loadElectionAndGroups = async () => {
    if (!electionId) return;
    try {
      setLoading(true);
      setError(null);
      const [electRes, groupsRes] = await Promise.all([
        api.get<Election>(`/elections/${electionId}`),
        api.get<VoterGroup[]>(`/elections/${electionId}/groups`),
      ]);
      setElection(electRes);
      setGroups(groupsRes);

      if (groupsRes.length > 0 && !selectedGroupId) {
        setSelectedGroupId(groupsRes[0].id);
      } else if (groupsRes.length === 0) {
        setSelectedGroupId(null);
      }
    } catch (err: any) {
      setError(err.message || 'Error al cargar la estructura electoral.');
    } finally {
      setLoading(false);
    }
  };

  const loadGroupDetails = async (groupId: string) => {
    try {
      const [levelsRes, nodesRes, contestsRes, filtersRes] = await Promise.all([
        api.get<HierarchyLevel[]>(`/groups/${groupId}/levels`),
        api.get<UnitNode[]>(`/groups/${groupId}/nodes/tree`),
        api.get<Contest[]>(`/groups/${groupId}/contests`),
        api.get<FilterDefinition[]>(`/groups/${groupId}/filters`),
      ]);
      setLevels(levelsRes);
      // Flatten nodes for table representation if needed
      const flattenNodes = (tree: UnitNode[]): UnitNode[] => {
        const flat: UnitNode[] = [];
        const walk = (items: UnitNode[]) => {
          for (const item of items) {
            flat.push(item);
            if (item.children && item.children.length > 0) {
              walk(item.children);
            }
          }
        };
        walk(tree);
        return flat;
      };
      setNodes(flattenNodes(nodesRes));
      setContests(contestsRes);
      setFilters(filtersRes);
    } catch (err: any) {
      console.error('Error al cargar datos del grupo:', err);
    }
  };

  useEffect(() => {
    loadElectionAndGroups();
  }, [electionId]);

  useEffect(() => {
    if (selectedGroupId) {
      loadGroupDetails(selectedGroupId);
    } else {
      setLevels([]);
      setNodes([]);
      setContests([]);
      setFilters([]);
    }
  }, [selectedGroupId]);

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim() || !newGroupCode.trim()) return;
    try {
      const res = await api.post<VoterGroup>(`/elections/${electionId}/groups`, {
        name: newGroupName.trim(),
        code: newGroupCode.trim().toUpperCase(),
      });
      setShowNewGroupModal(false);
      setNewGroupName('');
      setNewGroupCode('');
      await loadElectionAndGroups();
      setSelectedGroupId(res.id);
    } catch (err: any) {
      alert(err.message || 'Error al crear el grupo.');
    }
  };

  const handleCreateLevel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !newLevelName.trim()) return;
    try {
      await api.post(`/groups/${selectedGroupId}/levels`, {
        name: newLevelName.trim(),
      });
      setShowNewLevelModal(false);
      setNewLevelName('');
      loadGroupDetails(selectedGroupId);
    } catch (err: any) {
      alert(err.message || 'Error al agregar el nivel.');
    }
  };

  const handleCreateContest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !contestName.trim() || !contestScopeId) return;
    try {
      await api.post(`/groups/${selectedGroupId}/contests`, {
        name: contestName.trim(),
        scope_level_id: contestScopeId,
        allow_blank: contestAllowBlank,
        allow_null: contestAllowNull,
      });
      setShowNewContestModal(false);
      setContestName('');
      setContestScopeId('');
      loadGroupDetails(selectedGroupId);
    } catch (err: any) {
      alert(err.message || 'Error al crear el cargo.');
    }
  };

  const handleCreateFilter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !filterKey.trim() || !filterLabel.trim()) return;
    try {
      const allowed = filterValues
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      await api.post(`/groups/${selectedGroupId}/filters`, {
        key: filterKey.trim().toLowerCase(),
        label: filterLabel.trim(),
        allowed_values: allowed,
        is_required: filterRequired,
      });
      setShowNewFilterModal(false);
      setFilterKey('');
      setFilterLabel('');
      setFilterValues('');
      setFilterRequired(false);
      loadGroupDetails(selectedGroupId);
    } catch (err: any) {
      alert(err.message || 'Error al registrar el filtro.');
    }
  };

  const handleDeleteContest = async (contestId: string) => {
    if (!window.confirm('¿Está seguro de eliminar este cargo? Se perderán las circunscripciones y candidatos asociados.')) return;
    try {
      await api.delete(`/contests/${contestId}`);
      if (selectedGroupId) loadGroupDetails(selectedGroupId);
    } catch (err: any) {
      alert(err.message || 'Error al eliminar el cargo.');
    }
  };

  if (loading && !election) {
    return (
      <InstitutionalShell>
        <div className="py-24 text-center">
          <div className="inline-block animate-spin text-3xl mb-3">⚙️</div>
          <p className="text-sm font-semibold text-slate-600">Cargando arquitectura electoral...</p>
        </div>
      </InstitutionalShell>
    );
  }

  return (
    <InstitutionalShell>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Cabecera y Banner de Estado Estructural */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <div className="flex items-center space-x-2 text-xs text-slate-500 font-semibold mb-1">
              <Link to="/workspace" className="hover:text-civic-navy">
                Elecciones
              </Link>
              <span>/</span>
              <span className="text-slate-800">{election?.name}</span>
              <span>/</span>
              <span className="text-civic-navy font-bold">Estructura y Jerarquías</span>
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl font-black text-civic-navy tracking-tight">
              Arquitecto de Estructura y Cargos
            </h1>
          </div>

          <div className="flex items-center space-x-3">
            {isDraft ? (
              <button
                type="button"
                onClick={() => setShowPublishModal(true)}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition flex items-center space-x-2"
              >
                <span>📜 Publicar y Congelar Estructura</span>
              </button>
            ) : (
              <Link
                to={`/elections/${electionId}/candidates`}
                className="px-4 py-2 rounded-xl font-semibold text-xs bg-civic-navy text-white hover:bg-slate-800 transition"
              >
                Ir a Estudio de Candidatos ➔
              </Link>
            )}
          </div>
        </div>

        {/* Banner de Modo de Edición */}
        {isDraft ? (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between gap-3 text-emerald-900">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">✏️</span>
              <div>
                <span className="font-bold text-xs uppercase tracking-wider block">
                  Modo Diseño Activo (Editable)
                </span>
                <span className="text-xs text-emerald-800">
                  Puede agregar grupos, niveles, nodos, cargos y filtros dinámicos libremente antes de publicar.
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-slate-100 border border-slate-300 rounded-xl flex flex-wrap items-center justify-between gap-4 text-slate-800">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">🔒</span>
              <div>
                <span className="font-bold text-xs uppercase tracking-wider block text-slate-900">
                  Estructura Congelada por Publicación Oficial
                </span>
                <span className="text-xs text-slate-600">
                  La arquitectura electoral quedó sellada de forma inmutable. No se admiten modificaciones estructurales.
                </span>
              </div>
            </div>
            {election?.config_hash && (
              <CryptographicHashBadge hash={election.config_hash} label="config_hash" />
            )}
          </div>
        )}

        {/* Pestañas de Grupos de Votantes */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center space-x-2 overflow-x-auto">
              {groups.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setSelectedGroupId(g.id)}
                  className={`px-4 py-2 rounded-lg text-xs font-bold transition whitespace-nowrap flex items-center space-x-2 ${
                    selectedGroupId === g.id
                      ? 'bg-civic-navy text-white shadow-xs'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <span>{g.name}</span>
                  <span className="font-mono text-2xs px-1.5 py-0.2 rounded bg-black/20">
                    {g.code}
                  </span>
                </button>
              ))}
            </div>

            {isDraft && (
              <button
                type="button"
                onClick={() => setShowNewGroupModal(true)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 shadow-xs transition shrink-0"
              >
                + Nuevo Grupo
              </button>
            )}
          </div>

          {groups.length === 0 ? (
            <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
              <div className="text-4xl mb-3">👥</div>
              <h3 className="font-serif font-bold text-slate-800 mb-1">Sin Grupos de Votantes</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
                Toda elección requiere al menos un grupo de votantes (ej. Estudiantes, Docentes, Ciudadanos).
              </p>
              {isDraft && (
                <button
                  type="button"
                  onClick={() => setShowNewGroupModal(true)}
                  className="px-4 py-2 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800 transition"
                >
                  + Crear Primer Grupo
                </button>
              )}
            </div>
          ) : (
            selectedGroupId && (
              <div className="space-y-8">
                {/* 1. Escalera de Niveles Jerárquicos */}
                <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-serif font-bold text-base text-civic-navy">
                        Escalera de Niveles Jerárquicos
                      </h3>
                      <p className="text-xs text-slate-500">
                        Define la profundidad territorial u organizacional del grupo ({levels.length} niveles configurados).
                      </p>
                    </div>
                    {isDraft && (
                      <button
                        type="button"
                        onClick={() => setShowNewLevelModal(true)}
                        className="px-3 py-1.5 text-xs font-semibold bg-civic-navy text-white rounded-lg hover:bg-slate-800 transition"
                      >
                        + Añadir Nivel Extra
                      </button>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    {levels.map((lvl, index) => (
                      <div key={lvl.id} className="flex items-center space-x-2">
                        <div className="px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-200 flex items-center space-x-2 shadow-xs">
                          <span className="w-5 h-5 rounded-full bg-civic-navy text-white font-mono text-xs font-bold flex items-center justify-center">
                            {lvl.depth}
                          </span>
                          <span className="font-semibold text-xs text-slate-800">{lvl.name}</span>
                        </div>
                        {index < levels.length - 1 && (
                          <span className="text-slate-400 font-bold">➔</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. Árbol Jerárquico de Nodos (Materialized Path) */}
                <HierarchyTreeExplorer
                  groupId={selectedGroupId}
                  levels={levels}
                  nodes={nodes}
                  isDraft={isDraft}
                  onRefresh={() => loadGroupDetails(selectedGroupId)}
                />

                {/* 3. Matriz de Cargos y Circunscripciones Autogeneradas */}
                <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                    <div>
                      <h3 className="font-serif font-bold text-base text-civic-navy">
                        Cargos en Disputa y Circunscripciones
                      </h3>
                      <p className="text-xs text-slate-500">
                        Cargos postulables vinculados a su nivel de alcance territorial.
                      </p>
                    </div>
                    {isDraft && (
                      <button
                        type="button"
                        onClick={() => setShowNewContestModal(true)}
                        className="px-3 py-1.5 text-xs font-semibold bg-civic-navy text-white rounded-lg hover:bg-slate-800 transition"
                      >
                        + Nuevo Cargo
                      </button>
                    )}
                  </div>

                  {contests.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 text-xs">
                      No hay cargos registrados para este grupo. Agregue el primer cargo para autogenerar sus circunscripciones.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {contests.map((c) => (
                        <div
                          key={c.id}
                          className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition space-y-3"
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <span className="font-serif font-bold text-base text-slate-900 block">
                                {c.name}
                              </span>
                              <span className="inline-block px-2 py-0.5 rounded bg-civic-navy/10 text-civic-navy text-2xs font-bold uppercase mt-1">
                                Alcance: {c.scope_level_name || `Nivel ${c.scope_level_depth}`}
                              </span>
                            </div>
                            {isDraft && (
                              <button
                                type="button"
                                onClick={() => handleDeleteContest(c.id)}
                                className="text-slate-400 hover:text-red-600 text-xs p-1"
                                title="Eliminar cargo"
                              >
                                🗑️
                              </button>
                            )}
                          </div>

                          <div className="text-xs text-slate-600 flex items-center justify-between pt-2 border-t border-slate-200">
                            <div>
                              Circunscripciones:{' '}
                              <span className="font-bold text-civic-navy">
                                {c.constituencies_count} generadas
                              </span>
                            </div>
                            <div className="space-x-2 text-2xs text-slate-500">
                              {c.allow_blank && <span>⚪ Blanco</span>}
                              {c.allow_null && <span>✖️ Nulo</span>}
                            </div>
                          </div>

                          <div className="pt-1">
                            <Link
                              to={`/elections/${electionId}/candidates`}
                              className="text-xs font-semibold text-civic-navy hover:underline flex items-center space-x-1"
                            >
                              <span>Gestionar Candidatos de este Cargo</span>
                              <span>➔</span>
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 4. Filtros Dinámicos (Extra Attributes) */}
                <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                    <div>
                      <h3 className="font-serif font-bold text-base text-civic-navy">
                        Filtros Adicionales Dinámicos (JSONB)
                      </h3>
                      <p className="text-xs text-slate-500">
                        Atributos personalizados sin alterar el esquema para desgloses adicionales (ej. Turno, Sede).
                      </p>
                    </div>
                    {isDraft && (
                      <button
                        type="button"
                        onClick={() => setShowNewFilterModal(true)}
                        className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
                      >
                        + Nuevo Filtro
                      </button>
                    )}
                  </div>

                  {filters.length === 0 ? (
                    <div className="p-4 text-center text-slate-400 text-xs">
                      No hay filtros adicionales configurados para este grupo.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {filters.map((f) => (
                        <div key={f.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-slate-800">{f.label}</span>
                            <span className="font-mono text-2xs text-slate-500">{f.key}</span>
                          </div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {f.allowed_values.map((v, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-white text-slate-700 border border-slate-200 text-2xs font-mono">
                                {v}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          )}
        </div>
      </div>

      {/* Modal Nuevo Grupo */}
      {showNewGroupModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-sm p-6 space-y-4">
            <h4 className="font-serif font-bold text-base text-civic-navy">Crear Grupo de Votantes</h4>
            <form onSubmit={handleCreateGroup} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nombre</label>
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="Ej. ESTUDIANTES"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Código Corto</label>
                <input
                  type="text"
                  value={newGroupCode}
                  onChange={(e) => setNewGroupCode(e.target.value.toUpperCase())}
                  placeholder="Ej. EST"
                  required
                  className="w-full text-xs font-mono uppercase border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowNewGroupModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Nuevo Nivel */}
      {showNewLevelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-sm p-6 space-y-4">
            <h4 className="font-serif font-bold text-base text-civic-navy">Añadir Nivel Jerárquico Extra</h4>
            <p className="text-2xs text-slate-500">
              Se creará automáticamente como Nivel {levels.length + 1} de profundidad.
            </p>
            <form onSubmit={handleCreateLevel} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nombre del Nivel</label>
                <input
                  type="text"
                  value={newLevelName}
                  onChange={(e) => setNewLevelName(e.target.value)}
                  placeholder="Ej. Carrera, Departamento, Mesa"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowNewLevelModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800"
                >
                  Agregar Nivel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Nuevo Cargo */}
      {showNewContestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <h4 className="font-serif font-bold text-base text-civic-navy">Crear Cargo Electoral</h4>
            <form onSubmit={handleCreateContest} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nombre del Cargo</label>
                <input
                  type="text"
                  value={contestName}
                  onChange={(e) => setContestName(e.target.value)}
                  placeholder="Ej. Rector, Decano, Encargado de Carrera"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nivel Territorial de Alcance</label>
                <select
                  value={contestScopeId}
                  onChange={(e) => setContestScopeId(e.target.value)}
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                >
                  <option value="">Seleccione el nivel de alcance...</option>
                  {levels.map((lvl) => (
                    <option key={lvl.id} value={lvl.id}>
                      Nivel {lvl.depth}: {lvl.name}
                    </option>
                  ))}
                </select>
                <p className="text-2xs text-slate-500 mt-1">
                  Se generará automáticamente una circunscripción por cada nodo existente en este nivel.
                </p>
              </div>
              <div className="flex items-center space-x-4 pt-1">
                <label className="flex items-center space-x-2 text-xs text-slate-700 font-semibold cursor-pointer">
                  <input
                    type="checkbox"
                    checked={contestAllowBlank}
                    onChange={(e) => setContestAllowBlank(e.target.checked)}
                    className="rounded text-civic-navy"
                  />
                  <span>Permitir Voto en Blanco</span>
                </label>
                <label className="flex items-center space-x-2 text-xs text-slate-700 font-semibold cursor-pointer">
                  <input
                    type="checkbox"
                    checked={contestAllowNull}
                    onChange={(e) => setContestAllowNull(e.target.checked)}
                    className="rounded text-civic-navy"
                  />
                  <span>Permitir Voto Nulo</span>
                </label>
              </div>
              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowNewContestModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800"
                >
                  Crear Cargo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Nuevo Filtro */}
      {showNewFilterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-sm p-6 space-y-4">
            <h4 className="font-serif font-bold text-base text-civic-navy">Crear Filtro Dinámico</h4>
            <form onSubmit={handleCreateFilter} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Clave (Slug)</label>
                <input
                  type="text"
                  value={filterKey}
                  onChange={(e) => setFilterKey(e.target.value.toLowerCase())}
                  placeholder="Ej. turno, modalidad"
                  required
                  className="w-full text-xs font-mono border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Etiqueta Legible</label>
                <input
                  type="text"
                  value={filterLabel}
                  onChange={(e) => setFilterLabel(e.target.value)}
                  placeholder="Ej. Turno Académico"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Valores Permitidos (Separados por coma)
                </label>
                <input
                  type="text"
                  value={filterValues}
                  onChange={(e) => setFilterValues(e.target.value)}
                  placeholder="Mañana, Tarde, Noche"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>
              <label className="flex items-center space-x-2 text-xs text-slate-700 font-semibold cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterRequired}
                  onChange={(e) => setFilterRequired(e.target.checked)}
                  className="rounded text-civic-navy"
                />
                <span>Obligatorio al empadronar</span>
              </label>
              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowNewFilterModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800"
                >
                  Crear Filtro
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Ceremonia de Publicación */}
      {showPublishModal && election && (
        <PublicationCeremonyModal
          election={election}
          onClose={() => setShowPublishModal(false)}
          onPublished={(updated) => {
            setElection(updated);
            setShowPublishModal(false);
          }}
        />
      )}
    </InstitutionalShell>
  );
};
