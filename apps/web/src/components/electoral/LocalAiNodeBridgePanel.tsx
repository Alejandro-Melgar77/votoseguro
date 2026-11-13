import React, { useEffect, useState } from 'react';
import {
  Activity,
  Cpu,
  RefreshCw,
  Zap,
  Server,
  Terminal,
  AlertCircle,
  CheckCircle2,
  Lock,
  Unlock,
  Radio,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api';
import type {
  AiNodeStatusResponse,
  AiNodeTestInferenceResponse,
} from '@votoseguro/api-client';

interface LocalAiNodeBridgePanelProps {
  className?: string;
  defaultExpanded?: boolean;
}

export const LocalAiNodeBridgePanel: React.FC<LocalAiNodeBridgePanelProps> = ({
  className = '',
  defaultExpanded = true,
}) => {
  const [status, setStatus] = useState<AiNodeStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [updatingConfig, setUpdatingConfig] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);

  // Inferencia de prueba
  const [testPrompt, setTestPrompt] = useState<string>(
    'Verifica el estado del nodo y extrae los requisitos normativos del voto seguro.'
  );
  const [testingInference, setTestingInference] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<AiNodeTestInferenceResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<AiNodeStatusResponse>('/ai/node/status');
      const isOnline = data.online ?? data.is_online ?? false;

      // Si el backend en la nube dice que está offline (ej. recién despertando o BD con URL previa),
      // realizamos una verificación de respaldo directa desde el navegador hacia el túnel estático.
      if (!isOnline) {
        try {
          const t0 = performance.now();
          const directResp = await fetch(
            'https://repackage-remarry-reviving.ngrok-free.dev/v1/models',
            {
              headers: {
                'ngrok-skip-browser-warning': 'true',
              },
            }
          );
          if (directResp.ok) {
            const directLatency = Math.round(performance.now() - t0);
            data.online = true;
            data.is_online = true;
            data.latency_ms = directLatency;
            data.last_ping_latency_ms = directLatency;
            data.status_label = '🟢 NODO NEURONAL LOCAL CONECTADO (TÚNEL ESTÁTICO ACTIVO)';

            // Notificar y sincronizar a Render / Supabase automáticamente
            try {
              await api.post('/ai/node/ping', {
                llm_base_url: 'https://repackage-remarry-reviving.ngrok-free.dev/v1',
                model_name: 'votoseguro-lfm3',
                node_status: 'ONLINE',
                local_latency_ms: directLatency,
              });
            } catch (syncErr) {
              console.debug('Autosync ping warning:', syncErr);
            }
          }
        } catch (directErr) {
          console.debug('Direct browser check failed (tunnel truly offline):', directErr);
        }
      }

      setStatus(data);
    } catch (err: any) {
      setError(err.message || 'No se pudo contactar el estado del nodo neuronal.');
    } finally {
      setLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Enviar ping de sincronización forzada al backend con la URL estática
      try {
        await api.post('/ai/node/ping', {
          llm_base_url: 'https://repackage-remarry-reviving.ngrok-free.dev/v1',
          model_name: 'votoseguro-lfm3',
          node_status: 'ONLINE',
        });
      } catch (pingErr) {
        console.debug('Ping pre-fetch notice:', pingErr);
      }

      // 2. Ejecutar fetchStatus completo con verificación de respaldo
      await fetchStatus();
    } catch (err: any) {
      setError(err.message || 'Error al actualizar el estado del nodo neuronal.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Auto-polling opcional cada 30 segundos
    const timer = setInterval(() => {
      fetchStatus();
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  const handleToggleStrictMode = async () => {
    if (!status) return;
    setUpdatingConfig(true);
    try {
      const updated = await api.put<AiNodeStatusResponse>('/ai/node/config', {
        strict_neural_mode: !status.strict_neural_mode,
      });
      setStatus(updated);
    } catch (err: any) {
      alert(err.message || 'Error al actualizar el modo estricto neuronal.');
    } finally {
      setUpdatingConfig(false);
    }
  };

  const handleRunTestInference = async () => {
    setTestingInference(true);
    setTestError(null);
    setTestResult(null);
    try {
      const res = await api.post<AiNodeTestInferenceResponse>('/ai/node/test-inference', {
        prompt: testPrompt.trim() || undefined,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestError(err.message || 'Fallo durante la inferencia en vivo con el nodo de escritorio.');
    } finally {
      setTestingInference(false);
    }
  };

  const isConnected = status?.online ?? status?.is_online ?? false;
  const currentModelName = status?.model_name || status?.llm_model_name || 'votoseguro-lfm3';
  const currentLatency = status?.latency_ms ?? status?.last_ping_latency_ms;

  return (
    <div
      className={`bg-white rounded-xl shadow-card border border-stone-200 overflow-hidden ${className}`}
    >
      {/* Cabecera del Panel */}
      <div className="p-5 bg-stone-50/70 border-b border-stone-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg shadow-xs ${
              isConnected
                ? 'bg-purple-100 text-purple-700 border border-purple-300'
                : 'bg-amber-100 text-amber-700 border border-amber-300'
            }`}
          >
            {isConnected ? '🧠' : '⚙️'}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-title font-bold text-base text-civic-navy-900">
                Puente Neuronal de Escritorio (Sprint 2.5)
              </h3>
              <span
                className={`px-2 py-0.5 rounded-full text-2xs font-extrabold uppercase tracking-wider flex items-center space-x-1 ${
                  isConnected
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : 'bg-amber-100 text-amber-800 border border-amber-300'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isConnected ? 'bg-emerald-600 animate-ping' : 'bg-amber-500'
                  }`}
                />
                <span>
                  {isConnected
                    ? '🟢 NODO NEURONAL LOCAL CONECTADO (TÚNEL ESTÁTICO ACTIVO)'
                    : '🟠 NODO PC APAGADO (MODO DEGRADADO)'}
                </span>
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-0.5">
              Conexión directa entre Render y el modelo{' '}
              <strong className="text-stone-700 font-mono">
                {currentModelName}
              </strong>{' '}
              vía ngrok estático.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={handleManualRefresh}
            disabled={loading}
            className="px-3 py-1.5 bg-white hover:bg-stone-100 text-stone-700 border border-stone-300 rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow-2xs transition-colors disabled:opacity-50"
            title="Sondear y sincronizar estado de conexión con el túnel ngrok"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Actualizar</span>
          </button>
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg text-xs font-semibold transition-colors"
          >
            {isExpanded ? 'Contraer' : 'Expandir'}
          </button>
        </div>
      </div>

      {/* Contenido Expandible */}
      {isExpanded && (
        <div className="p-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Grilla de Métricas del Nodo */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Tarjeta 1: URL Túnel */}
            <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/50">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span className="font-semibold uppercase tracking-wider text-2xs">
                  Túnel Estático HTTPS
                </span>
                <Radio className="w-4 h-4 text-purple-600" />
              </div>
              <div
                className="font-mono text-xs font-bold text-stone-800 mt-2 truncate"
                title={status?.llm_base_url || 'https://repackage-remarry-reviving.ngrok-free.dev/v1'}
              >
                {status?.llm_base_url || 'https://repackage-remarry-reviving.ngrok-free.dev/v1'}
              </div>
              <div className="mt-1 flex items-center space-x-1 text-2xs text-stone-500">
                <span>Header obligatorio:</span>
                <code className="text-purple-700 font-mono bg-purple-50 px-1 rounded">
                  ngrok-skip-browser-warning
                </code>
              </div>
            </div>

            {/* Tarjeta 2: Modelo */}
            <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/50">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span className="font-semibold uppercase tracking-wider text-2xs">
                  Modelo Especializado
                </span>
                <Cpu className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="font-mono text-sm font-bold text-stone-900 mt-2">
                {currentModelName}
              </div>
              <div className="mt-1 text-2xs text-stone-500">
                Pesos cuantizados Q4_K_M (1.7B / 1.5B) + LoRA
              </div>
            </div>

            {/* Tarjeta 3: Latencia del Último Ping */}
            <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/50">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span className="font-semibold uppercase tracking-wider text-2xs">
                  Latencia del Túnel
                </span>
                <Activity className="w-4 h-4 text-blue-600" />
              </div>
              <div className="font-mono text-xl font-black text-civic-navy-900 mt-1">
                {currentLatency !== null && currentLatency !== undefined
                  ? `${Math.round(currentLatency)} ms`
                  : 'N/A'}
              </div>
              <div className="mt-1 text-2xs text-stone-500">
                Timeout de seguridad: {status?.timeout_seconds ?? 25.0} s
              </div>
            </div>

            {/* Tarjeta 4: Modo Estricto vs Permisivo */}
            <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/50 flex flex-col justify-between">
              <div className="flex items-center justify-between text-xs text-stone-500">
                <span className="font-semibold uppercase tracking-wider text-2xs">
                  Modo de Operación
                </span>
                {status?.strict_neural_mode ? (
                  <Lock className="w-4 h-4 text-red-600" />
                ) : (
                  <Unlock className="w-4 h-4 text-stone-600" />
                )}
              </div>
              <div className="mt-2 flex items-center justify-between">
                <div>
                  <span
                    className={`text-xs font-bold ${
                      status?.strict_neural_mode ? 'text-red-700' : 'text-stone-700'
                    }`}
                  >
                    {status?.strict_neural_mode
                      ? 'Estricto (503 si PC off)'
                      : 'Permisivo (Fallback)'}
                  </span>
                  <div className="text-2xs text-stone-500">
                    {status?.strict_neural_mode
                      ? 'Falla si el túnel no responde'
                      : 'Degrada a reglas deterministas'}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleToggleStrictMode}
                  disabled={updatingConfig}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    status?.strict_neural_mode ? 'bg-red-600' : 'bg-stone-300'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                      status?.strict_neural_mode ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Estado Informativo / Instrucciones de Lanzador */}
          <div className="p-4 bg-purple-50/60 rounded-xl border border-purple-200/80 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs text-purple-950">
            <div className="flex items-start space-x-3">
              <Terminal className="w-5 h-5 text-purple-700 shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold text-purple-900">
                  Lanzador de 1 Clic en esta PC de Escritorio:
                </strong>
                <p className="text-purple-800 text-xs mt-0.5">
                  Para encender el nodo ejecuta en Windows:{' '}
                  <code className="bg-purple-100 text-purple-900 font-mono px-1.5 py-0.5 rounded font-bold">
                    INICIAR_IA_LOCAL.bat
                  </code>{' '}
                  y para liberarlo:{' '}
                  <code className="bg-purple-100 text-purple-900 font-mono px-1.5 py-0.5 rounded font-bold">
                    DETENER_IA_LOCAL.bat
                  </code>
                  .
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <span className="font-mono text-2xs text-purple-700 bg-white/80 px-2 py-1 rounded border border-purple-200">
                Puerto Local: 11434
              </span>
            </div>
          </div>

          {/* Herramienta de Prueba de Inferencia en Vivo */}
          <div className="p-5 rounded-xl border border-stone-200 bg-white space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4 text-purple-600" />
                <h4 className="font-title font-bold text-sm text-civic-navy-900">
                  Prueba de Inferencia Neuronal en Vivo
                </h4>
              </div>
              <span className="text-2xs text-stone-500">
                Endpoint:{' '}
                <code className="font-mono bg-stone-100 px-1 py-0.5 rounded">
                  POST /api/v1/ai/node/test-inference
                </code>
              </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder="Escriba un prompt electoral de prueba..."
                className="flex-1 text-xs border border-stone-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-600"
              />
              <button
                type="button"
                onClick={handleRunTestInference}
                disabled={testingInference}
                className="px-4 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-colors disabled:opacity-50 shrink-0 shadow-xs"
              >
                <Zap className={`w-3.5 h-3.5 ${testingInference ? 'animate-bounce' : ''}`} />
                <span>
                  {testingInference ? 'Procesando en PC...' : 'Ejecutar Prueba en Vivo'}
                </span>
              </button>
            </div>

            {testError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs">
                ⚠️ {testError}
              </div>
            )}

            {testResult && (
              <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 text-xs space-y-3 animate-in fade-in">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-200 pb-2">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span className="font-bold text-stone-900">Inferencia Completada</span>
                    <span
                      className={`px-2 py-0.5 rounded text-2xs font-mono font-bold ${
                        testResult.ai_source.includes('NEURAL_TUNNEL')
                          ? 'bg-purple-100 text-purple-800 border border-purple-200'
                          : 'bg-amber-100 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {testResult.ai_source}
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 text-2xs text-stone-600">
                    <span>
                      Modelo: <strong>{testResult.model_name}</strong>
                    </span>
                    <span>
                      Latencia: <strong>{Math.round(testResult.latency_ms)} ms</strong>
                    </span>
                  </div>
                </div>

                {/* Salida de texto crudo */}
                <div>
                  <span className="text-2xs font-semibold uppercase text-stone-500 block mb-1">
                    Respuesta del Modelo:
                  </span>
                  <div className="p-3 bg-white rounded-lg border border-stone-200 text-stone-800 text-xs leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap font-sans">
                    {testResult.output_text}
                  </div>
                </div>

                {/* JSON estructurado parseado */}
                {testResult.parsed_json && (
                  <div>
                    <span className="text-2xs font-semibold uppercase text-stone-500 block mb-1">
                      JSON Estructurado Detectado:
                    </span>
                    <pre className="p-3 bg-stone-900 text-emerald-400 rounded-lg text-2xs font-mono overflow-x-auto max-h-40">
                      {JSON.stringify(testResult.parsed_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
