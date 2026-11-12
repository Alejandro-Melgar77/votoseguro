import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Activity,
  Radio,
  Users,
  Vote,
  ShieldCheck,
  TrendingUp,
  FileDown,
  RefreshCw,
  Clock,
  AlertTriangle,
  Building2,
  CheckCircle2,
} from 'lucide-react';
import { InstitutionalShell } from '@/components/layout/InstitutionalShell';
import { CryptographicHashBadge } from '@/components/electoral/CryptographicHashBadge';
import { ElectoralFaqAssistantWidget } from '@/components/electoral/ElectoralFaqAssistantWidget';
import { api, ApiError } from '@/lib/api';
import type { LiveDashboardSnapshot, AnomalyScanResponse } from '@votoseguro/api-client';

export const LiveMonitoringDashboardPage: React.FC = () => {
  const { electionId } = useParams<{ electionId: string }>();
  const [snapshot, setSnapshot] = useState<LiveDashboardSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [downloadingExport, setDownloadingExport] = useState<string | null>(null);
  const [anomaliesScan, setAnomaliesScan] = useState<AnomalyScanResponse | null>(null);
  const [scanningAnomalies, setScanningAnomalies] = useState<boolean>(false);
  const [simulateIfClean, setSimulateIfClean] = useState<boolean>(true);

  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const handleScanAnomalies = async () => {
    if (!electionId) return;
    setScanningAnomalies(true);
    try {
      const res = await api.post<AnomalyScanResponse>(
        `/ai/anomalies/${electionId}/explain?simulate_if_clean=${simulateIfClean}`
      );
      setAnomaliesScan(res);
    } catch (err: any) {
      console.error('Error analizando anomalías:', err);
    } finally {
      setScanningAnomalies(false);
    }
  };

  const fetchMetrics = async () => {
    if (!electionId) return;
    try {
      const data = await api.get<LiveDashboardSnapshot>(`/elections/${electionId}/live-metrics`);
      setSnapshot(data);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Error al consultar métricas en tiempo real');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!electionId) return;

    fetchMetrics();

    // 1. Establecer conexión WebSocket (S2-04)
    const token = localStorage.getItem('votoseguro_token') || '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const host = apiBase.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '');
    const wsUrl = `${protocol}//${host}/api/v1/elections/${electionId}/live?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'SNAPSHOT' && payload.data) {
            setSnapshot(payload.data);
          }
        } catch (e) {
          console.error('Error procesando mensaje WebSocket:', e);
        }
      };

      ws.onerror = () => {
        setWsConnected(false);
      };

      ws.onclose = () => {
        setWsConnected(false);
      };
    } catch (err) {
      setWsConnected(false);
    }

    // Polling de respaldo cada 12 segundos
    pollTimerRef.current = window.setInterval(() => {
      fetchMetrics();
    }, 12000);

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [electionId]);

  const handleDownload = async (type: 'results' | 'participation' | 'audit', format: 'pdf' | 'xlsx') => {
    if (!electionId) return;
    setDownloadingExport(`${type}-${format}`);
    try {
      const token = localStorage.getItem('votoseguro_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
      const url = `${apiBase}/elections/${electionId}/exports/${type}?format=${format}`;

      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Error en la descarga del reporte' }));
        alert(errorData.detail || 'No se pudo descargar el reporte solicitado');
        return;
      }

      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `VotoSeguro_${type}_${electionId.slice(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(a);
    } catch (err) {
      alert('Error de conexión al descargar reporte oficial');
    } finally {
      setDownloadingExport(null);
    }
  };

  return (
    <InstitutionalShell activeElectionId={electionId}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Encabezado Principal */}
        <div className="bg-white rounded-xl shadow-card border border-stone-200 p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <span className="p-2.5 bg-civic-navy-900 text-seal-emerald rounded-lg">
                  <Activity className="w-6 h-6" />
                </span>
                <div>
                  <h1 className="text-2xl font-title font-bold text-civic-navy-900">
                    Centro de Monitoreo en Tiempo Real
                  </h1>
                  <p className="text-sm text-stone-500 font-sans">
                    {snapshot?.election_name || 'Cargando elección...'} — Transmisión en vivo de participación
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center flex-wrap gap-3">
              {/* Indicador de conexión en vivo */}
              <div
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-mono font-medium ${
                  wsConnected
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}
              >
                <Radio className={`w-3.5 h-3.5 ${wsConnected ? 'animate-pulse text-emerald-600' : 'text-amber-600'}`} />
                <span>{wsConnected ? 'WebSocket Conectado (En Vivo)' : 'Sondeo Periódico Activo'}</span>
              </div>

              <button
                onClick={fetchMetrics}
                disabled={loading}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg text-xs font-medium transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Actualizar</span>
              </button>
            </div>
          </div>

          {/* Barra de Sellos Criptográficos */}
          {snapshot && (
            <div className="mt-6 pt-5 border-t border-stone-100 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-[11px] font-mono text-stone-400 uppercase tracking-wider mb-1">
                  Config Hash (RFC 8785)
                </p>
                <CryptographicHashBadge hash={snapshot.config_hash || 'PENDIENTE'} label="Config Hash" />
              </div>
              <div>
                <p className="text-[11px] font-mono text-stone-400 uppercase tracking-wider mb-1">
                  Roll Hash (Padrón Congelado)
                </p>
                <CryptographicHashBadge hash={snapshot.roll_hash || 'EN REGISTRO'} label="Roll Hash" />
              </div>
              <div>
                <p className="text-[11px] font-mono text-stone-400 uppercase tracking-wider mb-1">
                  Merkle Root (Árbol de Inclusión)
                </p>
                <CryptographicHashBadge hash={snapshot.merkle_root || 'EN REGISTRO'} label="Merkle Root" />
              </div>
            </div>
          )}
        </div>

        {/* Garantía Invariante #11 */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start space-x-3">
          <ShieldCheck className="w-5 h-5 text-seal-emerald shrink-0 mt-0.5" />
          <div className="text-xs text-emerald-900 leading-relaxed font-sans">
            <span className="font-semibold text-emerald-950">Garantía Invariante #11 de VotoSeguro:</span>{' '}
            Las métricas mostradas en este panel reflejan estrictamente el avance de participación ciudadana y el
            flujo de boletas en urna. Los conteos por candidato o preferencias políticas se encuentran
            criptográficamente sellados hasta la conclusión oficial del periodo electoral (VOTING_CLOSED).
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Barra de Exportación Rápida Oficial (S2-08) */}
        <div className="bg-white rounded-xl shadow-card border border-stone-200 p-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold text-civic-navy-900 font-title flex items-center space-x-2">
                <FileDown className="w-4 h-4 text-seal-emerald" />
                <span>Exportaciones Oficiales Selladas (PDF & Excel)</span>
              </h2>
              <p className="text-xs text-stone-500 font-sans">
                Genera actas institucionales con firmas y sellos criptográficos SHA-256 en memoria
              </p>
            </div>

            <div className="flex items-center flex-wrap gap-2">
              <button
                onClick={() => handleDownload('participation', 'pdf')}
                disabled={downloadingExport !== null}
                className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg text-xs font-medium inline-flex items-center space-x-1.5 transition-colors"
              >
                <span>Participación PDF</span>
              </button>
              <button
                onClick={() => handleDownload('participation', 'xlsx')}
                disabled={downloadingExport !== null}
                className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg text-xs font-medium inline-flex items-center space-x-1.5 transition-colors"
              >
                <span>Participación Excel</span>
              </button>
              <button
                onClick={() => handleDownload('audit', 'pdf')}
                disabled={downloadingExport !== null}
                className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg text-xs font-medium inline-flex items-center space-x-1.5 transition-colors"
              >
                <span>Auditoría PDF</span>
              </button>
              <button
                onClick={() => handleDownload('audit', 'xlsx')}
                disabled={downloadingExport !== null}
                className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg text-xs font-medium inline-flex items-center space-x-1.5 transition-colors"
              >
                <span>Auditoría Excel</span>
              </button>
            </div>
          </div>
        </div>

        {/* KPI Cards: Participación y Padrón */}
        {snapshot && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* KPI 1: Total Habilitados */}
            <div className="bg-white rounded-xl shadow-card border border-stone-200 p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-stone-500 uppercase tracking-wider font-sans">
                  Padrón Habilitado
                </span>
                <span className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                  <Users className="w-5 h-5" />
                </span>
              </div>
              <p className="mt-3 text-3xl font-bold font-title text-civic-navy-900">
                {snapshot.participation_metrics.total_eligible_active}
              </p>
              <div className="mt-2 text-xs text-stone-500 flex items-center justify-between">
                <span>Total inscritos: {snapshot.registration_metrics.total}</span>
                <span className="text-emerald-600 font-medium">
                  {snapshot.registration_metrics.activation_rate_pct}% activos
                </span>
              </div>
            </div>

            {/* KPI 2: Total Sufragios Emitidos */}
            <div className="bg-white rounded-xl shadow-card border border-stone-200 p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-stone-500 uppercase tracking-wider font-sans">
                  Votos en Urna
                </span>
                <span className="p-2 bg-emerald-50 text-seal-emerald rounded-lg">
                  <Vote className="w-5 h-5" />
                </span>
              </div>
              <p className="mt-3 text-3xl font-bold font-title text-civic-navy-900">
                {snapshot.participation_metrics.total_voted}
              </p>
              <p className="mt-2 text-xs text-stone-500">
                Boletas registradas y encadenadas por hash
              </p>
            </div>

            {/* KPI 3: Tasa de Participación */}
            <div className="bg-white rounded-xl shadow-card border border-stone-200 p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-stone-500 uppercase tracking-wider font-sans">
                  Participación Global
                </span>
                <span className="p-2 bg-amber-50 text-amber-600 rounded-lg">
                  <TrendingUp className="w-5 h-5" />
                </span>
              </div>
              <p className="mt-3 text-3xl font-bold font-title text-civic-navy-900">
                {snapshot.participation_metrics.participation_rate_pct}%
              </p>
              <div className="mt-3 w-full bg-stone-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-seal-emerald h-2 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(snapshot.participation_metrics.participation_rate_pct, 100)}%` }}
                />
              </div>
            </div>

            {/* KPI 4: Abstención Actual */}
            <div className="bg-white rounded-xl shadow-card border border-stone-200 p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-stone-500 uppercase tracking-wider font-sans">
                  Pendientes de Voto
                </span>
                <span className="p-2 bg-purple-50 text-purple-600 rounded-lg">
                  <Clock className="w-5 h-5" />
                </span>
              </div>
              <p className="mt-3 text-3xl font-bold font-title text-civic-navy-900">
                {snapshot.participation_metrics.abstention_count}
              </p>
              <p className="mt-2 text-xs text-stone-500">
                Electores que aún no han emitido sufragio
              </p>
            </div>
          </div>
        )}

        {/* Gráfica de Votos por Hora (S2-04) */}
        {snapshot && snapshot.hourly_votes_series && snapshot.hourly_votes_series.length > 0 && (
          <div className="bg-white rounded-xl shadow-card border border-stone-200 p-6">
            <h2 className="text-base font-bold text-civic-navy-900 font-title mb-4 flex items-center space-x-2">
              <Clock className="w-4 h-4 text-seal-emerald" />
              <span>Flujo de Boletas en Urna por Hora (Serie Temporal)</span>
            </h2>

            <div className="space-y-3">
              {snapshot.hourly_votes_series.map((bucket, idx) => {
                const maxInBucket = Math.max(...snapshot.hourly_votes_series.map((b) => b.ballots_cast), 1);
                const barWidth = Math.round((bucket.ballots_cast / maxInBucket) * 100);

                return (
                  <div key={idx} className="flex items-center text-xs">
                    <span className="w-28 font-mono text-stone-600 shrink-0">
                      {bucket.hour_label_local}
                    </span>
                    <div className="flex-1 bg-stone-100 rounded-md h-6 relative overflow-hidden flex items-center px-2 mr-3">
                      <div
                        className="absolute left-0 top-0 bottom-0 bg-civic-navy-800/80 rounded-md transition-all duration-300"
                        style={{ width: `${Math.max(barWidth, 2)}%` }}
                      />
                      <span className="relative z-10 font-mono font-bold text-civic-navy-900">
                        {bucket.ballots_cast} votos
                      </span>
                    </div>
                    <span className="w-28 text-right font-mono text-stone-500 shrink-0">
                      Acumulado: {bucket.cumulative_ballots}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Desglose Territorial por Segmento / Unidad (S2-04) */}
        {snapshot && (
          <div className="bg-white rounded-xl shadow-card border border-stone-200 overflow-hidden">
            <div className="p-6 border-b border-stone-100 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-civic-navy-900 font-title flex items-center space-x-2">
                  <Building2 className="w-4 h-4 text-seal-emerald" />
                  <span>Participación por Unidad / Territorio</span>
                </h2>
                <p className="text-xs text-stone-500 font-sans mt-0.5">
                  Avance de sufragio segmentado por facultades, carreras y sedes habilitadas
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-stone-200 text-xs font-sans">
                <thead className="bg-stone-50">
                  <tr>
                    <th className="px-6 py-3 text-left font-semibold text-stone-600 uppercase tracking-wider">
                      Grupo / Sector
                    </th>
                    <th className="px-6 py-3 text-left font-semibold text-stone-600 uppercase tracking-wider">
                      Unidad Territorial
                    </th>
                    <th className="px-6 py-3 text-left font-semibold text-stone-600 uppercase tracking-wider">
                      Ruta Jerárquica
                    </th>
                    <th className="px-6 py-3 text-right font-semibold text-stone-600 uppercase tracking-wider">
                      Padrón Activo
                    </th>
                    <th className="px-6 py-3 text-right font-semibold text-stone-600 uppercase tracking-wider">
                      Votos Emitidos
                    </th>
                    <th className="px-6 py-3 text-left font-semibold text-stone-600 uppercase tracking-wider">
                      Avance (%)
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 bg-white">
                  {snapshot.segment_breakdown.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-stone-400">
                        No hay segmentos registrados para esta elección.
                      </td>
                    </tr>
                  ) : (
                    snapshot.segment_breakdown.map((item, idx) => (
                      <tr key={idx} className="hover:bg-stone-50/60 transition-colors">
                        <td className="px-6 py-3.5 font-medium text-civic-navy-900">
                          {item.group_name}
                        </td>
                        <td className="px-6 py-3.5 font-medium text-stone-800">
                          {item.node_name}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-[11px] text-stone-500">
                          {item.node_path}
                        </td>
                        <td className="px-6 py-3.5 text-right font-mono text-stone-800">
                          {item.active_voters}
                        </td>
                        <td className="px-6 py-3.5 text-right font-mono font-bold text-civic-navy-900">
                          {item.votes_cast}
                        </td>
                        <td className="px-6 py-3.5">
                          <div className="flex items-center space-x-2">
                            <div className="w-24 bg-stone-100 rounded-full h-2 overflow-hidden">
                              <div
                                className="bg-seal-emerald h-2 rounded-full"
                                style={{ width: `${Math.min(item.participation_pct, 100)}%` }}
                              />
                            </div>
                            <span className="font-mono text-[11px] text-stone-700 font-semibold">
                              {item.participation_pct}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* IA-L1: Monitor de Anomalías Estadísticas y Explicación Asistida */}
        <div className="bg-white rounded-xl shadow-card border border-stone-200 overflow-hidden">
            <div className="p-6 border-b border-stone-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-civic-navy-900 font-title flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-emerald-600" />
                  <span>Monitor de Anomalías Estadísticas y Explicación Asistida (IA-L1)</span>
                </h2>
                <p className="text-xs text-stone-500 font-sans mt-0.5">
                  Análisis asistido con LiquidAI LFM3-1.7B sobre z-scores, picos horarios y asimetría de activación.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-stone-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simulateIfClean}
                    onChange={(e) => setSimulateIfClean(e.target.checked)}
                    className="rounded border-stone-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>Simulación si no hay anomalías</span>
                </label>

                <button
                  type="button"
                  onClick={handleScanAnomalies}
                  disabled={scanningAnomalies}
                  className="px-4 py-2 bg-[#0B132B] hover:bg-[#162550] text-white text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${scanningAnomalies ? 'animate-spin' : ''}`} />
                  <span>{scanningAnomalies ? 'Analizando con LFM3...' : 'Analizar Anomalías'}</span>
                </button>
              </div>
            </div>

            <div className="p-6">
              {!anomaliesScan && (
                <div className="text-center py-6 text-xs text-stone-400">
                  Haga clic en "Analizar Anomalías" para evaluar la distribución estadística de la elección con IA Local.
                </div>
              )}

              {anomaliesScan && anomaliesScan.anomalies.length === 0 && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  <div>
                    <strong>Distribución de Participación Estable:</strong> No se detectaron anomalías estadísticas
                    (z-scores |z| &lt; 1.8 y flujo horario regular).
                  </div>
                </div>
              )}

              {anomaliesScan && anomaliesScan.anomalies.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs text-stone-500">
                    <span>
                      Anomalías detectadas: <strong>{anomaliesScan.anomalies_found_count}</strong>
                      {anomaliesScan.is_simulation && ' (Incluye escenario de prueba)'}
                    </span>
                    <span className="font-mono text-[11px]">
                      Escaneado: {new Date(anomaliesScan.scanned_at_utc).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    {anomaliesScan.anomalies.map((anom, aIdx) => (
                      <div
                        key={aIdx}
                        className={`p-5 rounded-xl border transition-all ${
                          anom.severity === 'HIGH'
                            ? 'bg-red-50/40 border-red-200'
                            : anom.severity === 'MEDIUM'
                            ? 'bg-amber-50/40 border-amber-200'
                            : 'bg-blue-50/40 border-blue-200'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-200/60 pb-3 mb-3">
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                anom.severity === 'HIGH'
                                  ? 'bg-red-100 text-red-800'
                                  : anom.severity === 'MEDIUM'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-blue-100 text-blue-800'
                              }`}
                            >
                              Severidad: {anom.severity}
                            </span>
                            <span className="font-mono font-bold text-xs text-civic-navy-900">
                              {anom.code}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-[11px]">
                            <span className="px-2 py-0.5 rounded bg-stone-100 text-stone-700 font-mono">
                              Fuente: {anom.ai_source}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                              Decisión Humana Requerida
                            </span>
                          </div>
                        </div>

                        {/* Explicación en Español */}
                        <div className="text-xs text-stone-800 leading-relaxed mb-3">
                          <strong className="block text-stone-900 mb-1">Explicación Asistida (LFM3-1.7B):</strong>
                          {anom.explanation_es}
                        </div>

                        {/* Métricas Agregadas */}
                        <div className="bg-white/80 p-3 rounded-lg border border-stone-200/80 mb-3 text-xs grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {Object.entries(anom.metrics_summary).map(([k, val]) => (
                            <div key={k}>
                              <span className="text-[10px] text-stone-500 uppercase block font-semibold">
                                {k.replace(/_/g, ' ')}
                              </span>
                              <span className="font-mono text-stone-800 font-bold truncate block">
                                {typeof val === 'number' ? val : String(val)}
                              </span>
                            </div>
                          ))}
                        </div>

                        {/* Verificaciones recomendadas */}
                        {anom.recommended_checks.length > 0 && (
                          <div className="text-xs space-y-1">
                            <span className="font-semibold text-stone-700 block">
                              Verificaciones sugeridas para el Administrador:
                            </span>
                            <ul className="list-disc list-inside text-stone-600 space-y-0.5 pl-1">
                              {anom.recommended_checks.map((chk, cIdx) => (
                                <li key={cIdx}>{chk}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Widget Asistente Electoral Oficial RAG */}
      <ElectoralFaqAssistantWidget electionId={electionId} />
    </InstitutionalShell>
  );
};
