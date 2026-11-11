import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  CalendarDays,
  Play,
  Edit3,
  Clock,
  ArrowLeft,
  AlertCircle,
  RefreshCw,
  Mail,
  Send,
  Eye,
  CheckCircle2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { ElectionStateStepper } from '@/components/electoral/ElectionStateStepper';
import { PhaseCountdownClock } from '@/components/electoral/PhaseCountdownClock';
import { CryptographicHashBadge } from '@/components/electoral/CryptographicHashBadge';
import { SealStatusStamp } from '@/components/electoral/SealStatusStamp';
import { ScheduleEditModal } from '@/components/electoral/ScheduleEditModal';
import { ScheduleAuditTimeline } from '@/components/electoral/ScheduleAuditTimeline';
import type {
  Election,
  ScheduleChange,
  ScheduleUpdateRequest,
  NotificationOutboxItem,
} from '@votoseguro/api-client';
import { formatElectoralDateTime } from '@/lib/timezone';

export const ScheduleControlPanelPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();
  const { isAdminGeneral } = useAuth();

  const [election, setElection] = useState<Election | null>(null);
  const [history, setHistory] = useState<ScheduleChange[]>([]);
  const [outbox, setOutbox] = useState<NotificationOutboxItem[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<NotificationOutboxItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadElectionData = async () => {
    if (!electionId) return;
    setIsLoading(true);
    try {
      const [electionData, historyData, outboxData] = await Promise.all([
        api.get<Election>(`/elections/${electionId}`),
        api.get<ScheduleChange[]>(`/elections/${electionId}/schedule/history`),
        api.get<NotificationOutboxItem[]>(`/elections/${electionId}/notifications/outbox`).catch(() => [] as NotificationOutboxItem[]),
      ]);
      setElection(electionData);
      setHistory(historyData);
      setOutbox(outboxData);
    } catch (err: any) {
      setError(err.message || 'Error al cargar información del cronograma.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadElectionData();
  }, [electionId]);

  const handleOpenRegistrationNow = async () => {
    if (!election) return;
    if (
      !confirm(
        '¿Confirma la apertura INMEDIATA de la fase de registro? La hora de inicio se fijará a la hora actual del servidor.'
      )
    ) {
      return;
    }

    try {
      await api.post(`/elections/${election.id}/registration/open-now`);
      await loadElectionData();
    } catch (err: any) {
      alert(err.message || 'Error al abrir el registro.');
    }
  };

  const handleSaveSchedule = async (payload: ScheduleUpdateRequest) => {
    if (!election) return;
    setIsSubmitting(true);
    try {
      await api.put(`/elections/${election.id}/schedule`, payload);
      await loadElectionData();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading && !election) {
    return (
      <InstitutionalShell activeElectionId={electionId}>
        <div className="p-12 text-center text-stone-500 font-mono text-xs">
          Cargando cronograma electoral oficial...
        </div>
      </InstitutionalShell>
    );
  }

  if (!election) {
    return (
      <InstitutionalShell activeElectionId={electionId}>
        <div className="p-12 text-center text-seal-crimson font-semibold text-xs">
          Elección no encontrada.
        </div>
      </InstitutionalShell>
    );
  }

  // Determinar objetivo del reloj regresivo
  const getCountdownTarget = () => {
    switch (election.status) {
      case 'SCHEDULED':
        return {
          target: election.registration_opens_at,
          label: 'Apertura de la Fase de Registro de Votantes en:',
        };
      case 'REGISTRATION_OPEN':
        return {
          target: election.registration_closes_at,
          label: 'Cierre de Registro y Congelamiento de Padrón Electoral en:',
        };
      case 'REGISTRATION_CLOSED':
        return {
          target: election.voting_opens_at,
          label: 'Apertura Oficial de la Cabina de Votación en:',
        };
      case 'VOTING_OPEN':
        return {
          target: election.voting_closes_at,
          label: 'Cierre Definitivo de Recepción de Votos en:',
        };
      default:
        return null;
    }
  };

  const countdownTarget = getCountdownTarget();

  return (
    <InstitutionalShell activeElectionId={election.id} timezone={election.timezone}>
      <div className="space-y-6">
        {/* Cabecera y Navegación */}
        <div className="flex items-center justify-between">
          <Link
            to="/workspace"
            className="text-xs font-semibold text-stone-500 hover:text-civic-navy-900 flex items-center space-x-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Volver a Elecciones</span>
          </Link>

          <button
            onClick={loadElectionData}
            title="Recargar datos del servidor"
            className="p-1.5 rounded-lg border border-stone-300 hover:bg-stone-100 text-stone-600 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Título de la Elección */}
        <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-seal-emerald bg-seal-emerald/10 border border-seal-emerald/30 px-2 py-0.5 rounded">
                PROCESO ELECTORAL ACTIVO
              </span>
              <span className="text-xs font-mono text-stone-400">ID: {election.id}</span>
            </div>
            <h2 className="font-title text-2xl font-bold text-civic-navy-900 mt-1">
              {election.name}
            </h2>
            <p className="text-xs text-stone-500 font-mono mt-0.5">
              Zona Horaria Oficial: <span className="font-bold text-stone-700">{election.timezone}</span>
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            {election.status === 'SCHEDULED' && isAdminGeneral && (
              <button
                onClick={handleOpenRegistrationNow}
                className="px-4 py-2 bg-seal-emerald hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1.5"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Abrir Registro Ahora</span>
              </button>
            )}

            {isAdminGeneral && (
              <button
                onClick={() => setIsEditModalOpen(true)}
                className="px-4 py-2 bg-civic-navy-900 hover:bg-civic-navy-800 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1.5"
              >
                <Edit3 className="w-3.5 h-3.5 text-seal-amber" />
                <span>Modificar Cronograma</span>
              </button>
            )}
          </div>
        </div>

        {/* Sellos Criptográficos y de Estado */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SealStatusStamp status={election.status} />
          <CryptographicHashBadge
            label="Sello Criptográfico de Estructura"
            hash={election.config_hash}
            type="config"
          />
          <CryptographicHashBadge
            label="Sello Criptográfico del Padrón"
            hash={election.roll_hash}
            type="roll"
          />
        </div>

        {/* Línea de Tiempo de Estados Electorales (7 Fases) */}
        <ElectionStateStepper currentStatus={election.status} />

        {/* Reloj Regresivo Oficial Sincronizado */}
        {countdownTarget && (
          <PhaseCountdownClock
            targetDate={countdownTarget.target}
            label={countdownTarget.label}
            onExpire={loadElectionData}
          />
        )}

        {/* Tarjeta de Resumen de Horas */}
        <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-electoral">
          <h3 className="font-title text-sm font-bold text-civic-navy-900 border-b border-stone-200 pb-3 mb-4 flex items-center space-x-2">
            <Clock className="w-4 h-4 text-seal-emerald" />
            <span>Ventanas de Tiempo Establecidas</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            <div className="bg-stone-50 border border-stone-200 rounded-lg p-4 space-y-2">
              <span className="font-mono text-[10px] uppercase font-bold text-stone-500 block">
                Fase de Registro de Votantes
              </span>
              <div className="flex justify-between font-mono">
                <span className="text-stone-500">Inicio:</span>
                <span className="font-bold text-civic-navy-900">
                  {formatElectoralDateTime(election.registration_opens_at, election.timezone)}
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-stone-500">Cierre:</span>
                <span className="font-bold text-seal-crimson">
                  {formatElectoralDateTime(election.registration_closes_at, election.timezone)}
                </span>
              </div>
            </div>

            <div className="bg-stone-50 border border-stone-200 rounded-lg p-4 space-y-2">
              <span className="font-mono text-[10px] uppercase font-bold text-stone-500 block">
                Fase de Emisión del Sufragio
              </span>
              <div className="flex justify-between font-mono">
                <span className="text-stone-500">Apertura:</span>
                <span className="font-bold text-seal-emerald">
                  {formatElectoralDateTime(election.voting_opens_at, election.timezone)}
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-stone-500">Cierre Definitivo:</span>
                <span className="font-bold text-seal-crimson">
                  {formatElectoralDateTime(election.voting_closes_at, election.timezone)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Bitácora Histórica de Auditoría de Cronograma */}
        <ScheduleAuditTimeline changes={history} timezone={election.timezone} />

        {/* Bandeja de Notificaciones de Cronograma por Correo (S2-09) */}
        <div className="bg-white border border-stone-300 rounded-xl p-6 shadow-electoral space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-stone-200 pb-3">
            <div>
              <h3 className="font-title text-sm font-bold text-civic-navy-900 flex items-center space-x-2">
                <Mail className="w-4 h-4 text-seal-emerald" />
                <span>Bandeja de Notificaciones de Cronograma (S2-09)</span>
              </h3>
              <p className="text-xs text-stone-500">
                Correos despachados a votantes habilitados (`ACTIVE`) ante reprogramaciones o ajustes de calendario.
              </p>
            </div>
            <span className="px-2.5 py-1 bg-stone-100 rounded-lg text-xs font-mono font-bold text-stone-700">
              {outbox.length} notificaciones
            </span>
          </div>

          {outbox.length === 0 ? (
            <div className="p-8 text-center text-xs text-stone-500 font-mono">
              No se han emitido notificaciones de cambio de cronograma aún.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-stone-100 text-stone-600 font-mono text-[11px] border-b border-stone-200">
                    <th className="py-2.5 px-3">Destinatario</th>
                    <th className="py-2.5 px-3">Asunto</th>
                    <th className="py-2.5 px-3">Estado de Envío</th>
                    <th className="py-2.5 px-3">Fecha</th>
                    <th className="py-2.5 px-3 text-right">Contenido</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200">
                  {outbox.map((item) => (
                    <tr key={item.id} className="hover:bg-stone-50">
                      <td className="py-2.5 px-3">
                        <span className="font-semibold text-stone-800 block">{item.recipient_name}</span>
                        <span className="text-[11px] text-stone-500 font-mono">{item.recipient_email}</span>
                      </td>
                      <td className="py-2.5 px-3 text-stone-700 font-medium max-w-[260px] truncate" title={item.subject}>
                        {item.subject}
                      </td>
                      <td className="py-2.5 px-3">
                        {item.delivery_status === 'SENT_SMTP' ? (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Enviado SMTP</span>
                          </span>
                        ) : item.delivery_status === 'STORED_DEMO_OUTBOX' ? (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                            <Send className="w-3 h-3" />
                            <span>Outbox Demo</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800">
                            <AlertCircle className="w-3 h-3" />
                            <span>Fallo</span>
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-stone-500 font-mono text-[11px]">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => setSelectedEmail(item)}
                          className="px-2 py-1 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded text-xs font-bold inline-flex items-center space-x-1 transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Ver</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal de Lectura de Correo Notificado */}
      {selectedEmail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-civic-navy-950/70 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-stone-300 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-title text-base font-bold text-civic-navy-900 flex items-center space-x-2">
                <Mail className="w-5 h-5 text-seal-emerald" />
                <span>Notificación de Cambio de Cronograma</span>
              </h3>
              <button
                onClick={() => setSelectedEmail(null)}
                className="text-stone-400 hover:text-stone-600 font-bold text-xl"
              >
                &times;
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="bg-stone-50 p-3 rounded-lg border border-stone-200 space-y-1">
                <div>
                  <span className="font-bold text-stone-600">Para:</span>{' '}
                  <span className="font-mono text-stone-900">{selectedEmail.recipient_name} ({selectedEmail.recipient_email})</span>
                </div>
                <div>
                  <span className="font-bold text-stone-600">Asunto:</span>{' '}
                  <span className="font-semibold text-stone-900">{selectedEmail.subject}</span>
                </div>
                <div>
                  <span className="font-bold text-stone-600">Fecha:</span>{' '}
                  <span className="font-mono text-stone-600">{new Date(selectedEmail.created_at).toLocaleString()}</span>
                </div>
              </div>

              <div>
                <span className="font-bold text-stone-700 block mb-1">Cuerpo del Mensaje:</span>
                <div className="p-4 bg-stone-100 rounded-lg font-mono text-[11px] text-stone-800 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                  {selectedEmail.body_text}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedEmail(null)}
                className="px-4 py-1.5 bg-civic-navy-900 text-white rounded-lg text-xs font-bold hover:bg-civic-navy-800"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Edición de Cronograma */}
      {isEditModalOpen && (
        <ScheduleEditModal
          election={election}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleSaveSchedule}
          isLoading={isSubmitting}
        />
      )}
    </InstitutionalShell>
  );
};
