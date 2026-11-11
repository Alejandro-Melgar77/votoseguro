import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Election,
  VoterGroup,
  Contest,
  Constituency,
  Candidate,
} from '@votoseguro/api-client';
import { api } from '@/lib/api';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { OfficialBallotPreviewCard } from '@/components/electoral/OfficialBallotPreviewCard';

export const CandidatesBallotStudioPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();

  const [election, setElection] = useState<Election | null>(null);
  const [groups, setGroups] = useState<VoterGroup[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string>('');

  const [contests, setContests] = useState<Contest[]>([]);
  const [selectedContestId, setSelectedContestId] = useState<string>('');

  const [constituencies, setConstituencies] = useState<Constituency[]>([]);
  const [selectedConstituencyId, setSelectedConstituencyId] = useState<string>('');

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal para Candidato
  const [showCandidateModal, setShowCandidateModal] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState<Candidate | null>(null);
  const [candName, setCandName] = useState('');
  const [candParty, setCandParty] = useState('');
  const [candPhotoUrl, setCandPhotoUrl] = useState('');
  const [candSubmitting, setCandSubmitting] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [candError, setCandError] = useState<string | null>(null);

  const isDraft = election?.status === 'DRAFT';

  const loadInitialData = async () => {
    if (!electionId) return;
    try {
      setLoading(true);
      const [electRes, groupsRes] = await Promise.all([
        api.get<Election>(`/elections/${electionId}`),
        api.get<VoterGroup[]>(`/elections/${electionId}/groups`),
      ]);
      setElection(electRes);
      setGroups(groupsRes);
      if (groupsRes.length > 0) {
        setSelectedGroupId(groupsRes[0].id);
      }
    } catch (err: any) {
      console.error('Error al cargar datos base:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, [electionId]);

  useEffect(() => {
    if (!selectedGroupId) {
      setContests([]);
      setSelectedContestId('');
      return;
    }
    const loadContests = async () => {
      try {
        const res = await api.get<Contest[]>(`/groups/${selectedGroupId}/contests`);
        setContests(res);
        if (res.length > 0) {
          setSelectedContestId(res[0].id);
        } else {
          setSelectedContestId('');
        }
      } catch (err: any) {
        console.error('Error al cargar cargos:', err);
      }
    };
    loadContests();
  }, [selectedGroupId]);

  useEffect(() => {
    if (!selectedContestId) {
      setConstituencies([]);
      setSelectedConstituencyId('');
      return;
    }
    const loadConstituencies = async () => {
      try {
        const res = await api.get<Constituency[]>(`/contests/${selectedContestId}/constituencies`);
        setConstituencies(res);
        if (res.length > 0) {
          setSelectedConstituencyId(res[0].id);
        } else {
          setSelectedConstituencyId('');
        }
      } catch (err: any) {
        console.error('Error al cargar circunscripciones:', err);
      }
    };
    loadConstituencies();
  }, [selectedContestId]);

  const loadCandidates = async (constituencyId: string) => {
    try {
      const res = await api.get<Candidate[]>(`/constituencies/${constituencyId}/candidates`);
      setCandidates(res);
    } catch (err: any) {
      console.error('Error al cargar candidatos:', err);
    }
  };

  useEffect(() => {
    if (selectedConstituencyId) {
      loadCandidates(selectedConstituencyId);
    } else {
      setCandidates([]);
    }
  }, [selectedConstituencyId]);

  const openAddModal = () => {
    setEditingCandidate(null);
    setCandName('');
    setCandParty('');
    setCandPhotoUrl('');
    setCandError(null);
    setShowCandidateModal(true);
  };

  const openEditModal = (c: Candidate) => {
    setEditingCandidate(c);
    setCandName(c.name);
    setCandParty(c.party_or_front || '');
    setCandPhotoUrl(c.photo_url || '');
    setCandError(null);
    setShowCandidateModal(true);
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files ? e.target.files[0] : null;
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      setCandError('La fotografía no debe superar 2 MB de tamaño.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadingPhoto(true);
      setCandError(null);
      const res = await api.post<{ photo_url: string }>('/candidates/upload-photo', formData);
      setCandPhotoUrl(res.photo_url);
    } catch (err: any) {
      setCandError(err.message || 'Error al validar o subir la imagen.');
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleSaveCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedConstituencyId || !candName.trim()) return;

    try {
      setCandSubmitting(true);
      setCandError(null);

      if (editingCandidate) {
        await api.put(`/candidates/${editingCandidate.id}`, {
          name: candName.trim(),
          party_or_front: candParty.trim() || null,
          photo_url: candPhotoUrl.trim() || null,
        });
      } else {
        await api.post(`/constituencies/${selectedConstituencyId}/candidates`, {
          name: candName.trim(),
          party_or_front: candParty.trim() || null,
          photo_url: candPhotoUrl.trim() || null,
        });
      }

      setShowCandidateModal(false);
      loadCandidates(selectedConstituencyId);
    } catch (err: any) {
      setCandError(err.message || 'Error al guardar el candidato.');
    } finally {
      setCandSubmitting(false);
    }
  };

  const handleDeleteCandidate = async (candidateId: string, name: string) => {
    if (!window.confirm(`¿Desea retirar al candidato '${name}' de esta papeleta?`)) return;
    try {
      await api.delete(`/candidates/${candidateId}`);
      if (selectedConstituencyId) loadCandidates(selectedConstituencyId);
    } catch (err: any) {
      alert(err.message || 'Error al eliminar el candidato.');
    }
  };

  const handleMoveCandidate = async (candidateId: string, direction: 'UP' | 'DOWN') => {
    const sorted = [...candidates].sort((a, b) => a.ballot_order - b.ballot_order);
    const index = sorted.findIndex((c) => c.id === candidateId);
    if (index === -1) return;

    const targetIndex = direction === 'UP' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= sorted.length) return;

    // Swap
    const temp = sorted[index];
    sorted[index] = sorted[targetIndex];
    sorted[targetIndex] = temp;

    try {
      await api.put(`/constituencies/${selectedConstituencyId}/candidates/reorder`, {
        ordered_candidate_ids: sorted.map((c) => c.id),
      });
      loadCandidates(selectedConstituencyId);
    } catch (err: any) {
      alert(err.message || 'Error al reordenar candidatos.');
    }
  };

  const currentContest = contests.find((c) => c.id === selectedContestId);
  const currentConstituency = constituencies.find((c) => c.id === selectedConstituencyId);

  return (
    <InstitutionalShell>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Cabecera */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <div className="flex items-center space-x-2 text-xs text-slate-500 font-semibold mb-1">
              <Link to="/workspace" className="hover:text-civic-navy">
                Elecciones
              </Link>
              <span>/</span>
              <span className="text-slate-800">{election?.name}</span>
              <span>/</span>
              <span className="text-civic-navy font-bold">Candidatos y Papeleta</span>
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl font-black text-civic-navy tracking-tight">
              Estudio de Candidatos y Simulador de Papeleta
            </h1>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              to={`/elections/${electionId}/structure`}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              ⬅ Volver a Estructura
            </Link>
          </div>
        </div>

        {/* Cascada de Selección: Grupo -> Cargo -> Circunscripción */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          {/* 1. Grupo */}
          <div>
            <label className="block text-2xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              1. Grupo de Votantes
            </label>
            <select
              value={selectedGroupId}
              onChange={(e) => setSelectedGroupId(e.target.value)}
              className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-3 py-2 bg-slate-50"
            >
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name} ({g.code})
                </option>
              ))}
            </select>
          </div>

          {/* 2. Cargo */}
          <div>
            <label className="block text-2xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              2. Cargo en Disputa
            </label>
            <select
              value={selectedContestId}
              onChange={(e) => setSelectedContestId(e.target.value)}
              disabled={contests.length === 0}
              className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 disabled:opacity-50"
            >
              {contests.length === 0 && <option value="">Sin cargos en este grupo</option>}
              {contests.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} (Alcance: {c.scope_level_name || `Nivel ${c.scope_level_depth}`})
                </option>
              ))}
            </select>
          </div>

          {/* 3. Circunscripción */}
          <div>
            <label className="block text-2xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              3. Circunscripción Territorial
            </label>
            <select
              value={selectedConstituencyId}
              onChange={(e) => setSelectedConstituencyId(e.target.value)}
              disabled={constituencies.length === 0}
              className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 disabled:opacity-50"
            >
              {constituencies.length === 0 && <option value="">Sin circunscripciones</option>}
              {constituencies.map((constituency) => (
                <option key={constituency.id} value={constituency.id}>
                  {constituency.node_name} ({constituency.node_code})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Zona Principal Dividida: Lista de Candidatos (Izq) vs Simulador de Papeleta Oficial (Der) */}
        {!selectedConstituencyId ? (
          <div className="p-16 text-center bg-white rounded-xl border border-dashed border-slate-300 text-slate-400 text-sm">
            Seleccione un grupo, cargo y circunscripción para gestionar sus candidatos.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Columna Izquierda: Lista de Candidatos y Orden */}
            <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <div>
                  <h3 className="font-serif font-bold text-lg text-civic-navy">
                    Candidatos Registrados
                  </h3>
                  <p className="text-xs text-slate-500">
                    Posición en la papeleta para {currentConstituency?.node_name}.
                  </p>
                </div>

                {isDraft && (
                  <button
                    type="button"
                    onClick={openAddModal}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-civic-navy text-white hover:bg-slate-800 transition shadow-xs"
                  >
                    + Registrar Candidato
                  </button>
                )}
              </div>

              {candidates.length === 0 ? (
                <div className="p-12 text-center border-2 border-dashed border-slate-200 rounded-xl space-y-3">
                  <div className="text-3xl">👤</div>
                  <div className="text-sm font-bold text-slate-700">Sin Candidatos Registrados</div>
                  <p className="text-xs text-slate-500 max-w-xs mx-auto">
                    Recuerde que para publicar la elección, toda circunscripción debe tener al menos un candidato registrado.
                  </p>
                  {isDraft && (
                    <button
                      type="button"
                      onClick={openAddModal}
                      className="px-4 py-2 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800 transition"
                    >
                      + Registrar Primer Candidato
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {candidates
                    .sort((a, b) => a.ballot_order - b.ballot_order)
                    .map((c, index) => (
                      <div
                        key={c.id}
                        className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 hover:bg-slate-50 transition flex items-center justify-between gap-4"
                      >
                        <div className="flex items-center space-x-3.5">
                          <span className="w-7 h-7 rounded-full bg-civic-navy text-white font-mono font-bold text-xs flex items-center justify-center shrink-0">
                            {c.ballot_order}
                          </span>

                          <div className="w-12 h-12 rounded-full bg-slate-200 overflow-hidden border border-slate-300 flex items-center justify-center shrink-0">
                            {c.photo_url ? (
                              <img src={c.photo_url} alt={c.name} className="w-full h-full object-cover" />
                            ) : (
                              <span className="text-slate-400 text-lg">👤</span>
                            )}
                          </div>

                          <div>
                            <span className="font-serif font-bold text-sm text-slate-900 block">
                              {c.name}
                            </span>
                            {c.party_or_front && (
                              <span className="inline-block px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-mono text-2xs uppercase mt-0.5 font-semibold">
                                {c.party_or_front}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Controles de Orden y Acciones */}
                        {isDraft && (
                          <div className="flex items-center space-x-1.5 shrink-0">
                            <button
                              type="button"
                              disabled={index === 0}
                              onClick={() => handleMoveCandidate(c.id, 'UP')}
                              className="p-1.5 rounded hover:bg-slate-200 disabled:opacity-20 text-slate-700 text-xs"
                              title="Subir orden"
                            >
                              ▲
                            </button>
                            <button
                              type="button"
                              disabled={index === candidates.length - 1}
                              onClick={() => handleMoveCandidate(c.id, 'DOWN')}
                              className="p-1.5 rounded hover:bg-slate-200 disabled:opacity-20 text-slate-700 text-xs"
                              title="Bajar orden"
                            >
                              ▼
                            </button>
                            <button
                              type="button"
                              onClick={() => openEditModal(c)}
                              className="px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-200 rounded"
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteCandidate(c.id, c.name)}
                              className="p-1 text-xs text-red-600 hover:bg-red-50 rounded"
                              title="Eliminar candidato"
                            >
                              🗑️
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </div>

            {/* Columna Derecha: Simulador Visual de Papeleta Oficial */}
            <div className="lg:col-span-5 space-y-3">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider text-center">
                Simulador de Papeleta Oficial en Tiempo Real
              </div>
              <OfficialBallotPreviewCard
                electionName={election?.name || 'Elección Oficial'}
                contestName={currentContest?.name || 'Cargo'}
                constituencyName={currentConstituency?.node_name || 'Circunscripción'}
                allowBlank={currentContest?.allow_blank ?? true}
                allowNull={currentContest?.allow_null ?? true}
                candidates={candidates}
              />
            </div>
          </div>
        )}
      </div>

      {/* Modal para Registro / Edición de Candidato */}
      {showCandidateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <h4 className="font-serif font-bold text-base text-civic-navy">
                {editingCandidate ? 'Editar Candidato' : 'Registrar Nuevo Candidato'}
              </h4>
              <button
                type="button"
                onClick={() => setShowCandidateModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                &times;
              </button>
            </div>

            {candError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {candError}
              </div>
            )}

            <form onSubmit={handleSaveCandidate} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nombre Completo</label>
                <input
                  type="text"
                  value={candName}
                  onChange={(e) => setCandName(e.target.value)}
                  placeholder="Ej. Ing. Mario Mendoza"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Partido, Sigla o Frente Político
                </label>
                <input
                  type="text"
                  value={candParty}
                  onChange={(e) => setCandParty(e.target.value)}
                  placeholder="Ej. FRENTE TECNOLOGÍA UNIDA"
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>

              {/* Subida y Validación de Fotografía */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700">
                  Fotografía Oficial (JPEG, PNG o WEBP - Máx. 2MB)
                </label>
                <div className="flex items-center space-x-3">
                  <div className="w-14 h-14 rounded-full bg-slate-100 border border-slate-300 overflow-hidden flex items-center justify-center shrink-0">
                    {candPhotoUrl ? (
                      <img src={candPhotoUrl} alt="Preview" className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-slate-400 text-xl">👤</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handlePhotoUpload}
                      disabled={uploadingPhoto}
                      className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-civic-navy file:text-white hover:file:bg-slate-800 border border-slate-200 rounded-lg"
                    />
                    {uploadingPhoto && (
                      <p className="text-2xs text-slate-500 mt-1">Validando formato y dimensiones...</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="pt-3 flex justify-end space-x-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowCandidateModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={candSubmitting || uploadingPhoto}
                  className="px-4 py-2 text-xs font-bold text-white bg-civic-navy rounded-lg hover:bg-slate-800 disabled:opacity-50"
                >
                  {candSubmitting ? 'Guardando...' : 'Guardar Candidato'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </InstitutionalShell>
  );
};
