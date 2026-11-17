import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Vote,
  Shield,
  KeyRound,
  Eye,
  Cpu,
  ChevronRight,
  CheckCircle2,
  Lock,
  FileText,
  Volume2,
  Sparkles,
  ArrowLeft,
  ExternalLink,
  Layers,
  Terminal,
  AlertTriangle,
  QrCode,
} from 'lucide-react';

export const UserAndAdminManualPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'voter' | 'admin' | 'trustee' | 'observer' | 'local_ai'>('voter');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Barra de Navegación Superior */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link
              to="/"
              className="flex items-center space-x-2 text-slate-400 hover:text-slate-200 transition-colors mr-3"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="text-sm font-medium">Volver</span>
            </Link>
            <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">
              <BookOpen className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
                <span>Centro de Documentación y Manuales</span>
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/30">
                  v3.0.0
                </span>
              </h1>
              <p className="text-xs text-slate-400">VotoSeguro v2 — INF 422 SB (UAGRM)</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              to="/audit-portal"
              className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition flex items-center space-x-1.5"
            >
              <Eye className="w-3.5 h-3.5 text-cyan-400" />
              <span>Portal de Auditoría</span>
            </Link>
            <Link
              to="/vote"
              className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition flex items-center space-x-1.5 shadow-sm"
            >
              <Vote className="w-3.5 h-3.5" />
              <span>Ir a Votar</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Contenido Principal con Pestañas */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
        {/* Selector de Roles */}
        <div className="flex flex-wrap gap-2 p-1.5 bg-slate-900 border border-slate-800 rounded-xl mb-8">
          <button
            onClick={() => setActiveTab('voter')}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'voter'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Vote className="w-4 h-4" />
            <span>1. Guía del Elector</span>
          </button>

          <button
            onClick={() => setActiveTab('admin')}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'admin'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>2. Administrador General</span>
          </button>

          <button
            onClick={() => setActiveTab('trustee')}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'trustee'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <KeyRound className="w-4 h-4" />
            <span>3. Custodios de Shamir</span>
          </button>

          <button
            onClick={() => setActiveTab('observer')}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'observer'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Eye className="w-4 h-4" />
            <span>4. Delegados y Auditores</span>
          </button>

          <button
            onClick={() => setActiveTab('local_ai')}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'local_ai'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Cpu className="w-4 h-4" />
            <span>5. Nodo Neuronal Local</span>
          </button>
        </div>

        {/* TAB 1: GUÍA DEL ELECTOR */}
        {activeTab === 'voter' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
                  <Vote className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Manual del Elector — Votación Secreta y Auditable</h2>
                  <p className="text-sm text-slate-400">
                    Instrucciones para activación de cuenta, cabina de sufragio con cifrado Paillier y comprobante digital.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
                  <h3 className="text-base font-semibold text-emerald-400 flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Paso 1: Activación y Padrón Electoral</span>
                  </h3>
                  <ul className="text-sm text-slate-300 space-y-2 list-disc list-inside">
                    <li>
                      <strong>Por correo:</strong> Abra el enlace <code className="text-emerald-300">/register/:token</code> recibido institucionalmente.
                    </li>
                    <li>
                      <strong>Autoinscripción:</strong> Si el registro está abierto, ingrese su CI y carrera en el portal de registro.
                    </li>
                    <li>
                      <strong>Escaneo OCR (IA-L3):</strong> Apunte la cámara a su cédula para extracción instantánea sin teclear.
                    </li>
                    <li>
                      <strong>Validación Facial (IA-L4):</strong> Compruebe prueba de vida. Las imágenes se procesan en RAM y nunca se guardan (Invariante #15).
                    </li>
                  </ul>
                </div>

                <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
                  <h3 className="text-base font-semibold text-emerald-400 flex items-center space-x-2">
                    <Lock className="w-4 h-4" />
                    <span>Paso 2: Cabina de Sufragio Cifrada</span>
                  </h3>
                  <ul className="text-sm text-slate-300 space-y-2 list-disc list-inside">
                    <li>
                      Ingrese a <code className="text-emerald-300">/vote</code> con su CI y su credencial secreta (ej. <code>VS-2026-X8F9</code>).
                    </li>
                    <li>
                      Seleccione su lengua materna: <strong>Español, Quechua, Aymara o Guaraní</strong>.
                    </li>
                    <li>
                      Active el <strong>Modo Voz Asistida (IA-L4)</strong> si requiere locución completa y comandos por micrófono.
                    </li>
                    <li>
                      Emita su selección (Candidato, Blanco o Nulo) con cifrado homomórfico Paillier y nullifier HMAC determinista.
                    </li>
                  </ul>
                </div>

                <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3 md:col-span-2">
                  <h3 className="text-base font-semibold text-emerald-400 flex items-center space-x-2">
                    <QrCode className="w-4 h-4" />
                    <span>Paso 3: Comprobante y Verificación Criptográfica</span>
                  </h3>
                  <div className="text-sm text-slate-300 space-y-2">
                    <p>
                      Al concluir, descargará su comprobante con el hash SHA-256 de 64 caracteres (<code className="text-emerald-300">receipt_hash</code>).
                    </p>
                    <p>
                      Puede verificar que su papeleta fue depositada sin adulteraciones ingresando a{' '}
                      <Link to="/verify-receipt" className="text-cyan-400 underline hover:text-cyan-300">
                        /verify-receipt
                      </Link>{' '}
                      y comprobando la prueba de inclusión en el <strong>Árbol de Merkle</strong>.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: ADMINISTRADOR GENERAL */}
        {activeTab === 'admin' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
                  <Shield className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Manual del Administrador General (ADMIN_GENERAL)</h2>
                  <p className="text-sm text-slate-400">
                    Gobierno de la elección, ceremonia de llaves, padrón, monitoreo en vivo y escrutinio homomórfico.
                  </p>
                </div>
              </div>

              <div className="space-y-6 mt-6">
                <div className="border border-slate-800 rounded-xl p-5 bg-slate-950/40">
                  <h3 className="text-base font-semibold text-emerald-400 mb-2">1. Ciclo de Vida y Transiciones Invariantes</h3>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-2.5 py-1 bg-slate-800 rounded border border-slate-700">DRAFT</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 self-center" />
                    <span className="px-2.5 py-1 bg-blue-900/40 text-blue-300 rounded border border-blue-800">SCHEDULED</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 self-center" />
                    <span className="px-2.5 py-1 bg-amber-900/40 text-amber-300 rounded border border-amber-800">REGISTRATION_OPEN</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 self-center" />
                    <span className="px-2.5 py-1 bg-purple-900/40 text-purple-300 rounded border border-purple-800">REGISTRATION_CLOSED</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 self-center" />
                    <span className="px-2.5 py-1 bg-emerald-900/40 text-emerald-300 rounded border border-emerald-800">VOTING_OPEN</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 self-center" />
                    <span className="px-2.5 py-1 bg-orange-900/40 text-orange-300 rounded border border-orange-800">VOTING_CLOSED</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 self-center" />
                    <span className="px-2.5 py-1 bg-teal-900/40 text-teal-300 rounded border border-teal-800">TALLIED</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <h4 className="text-sm font-semibold text-white flex items-center space-x-2">
                      <KeyRound className="w-4 h-4 text-amber-400" />
                      <span>Ceremonia Paillier + Shamir</span>
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Genere las llaves homomórficas en <code>/ceremony</code>. La clave privada se fragmenta en $n$ custodios con umbral $k$ y se destruye en memoria (Invariante #20).
                    </p>
                  </div>

                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <h4 className="text-sm font-semibold text-white flex items-center space-x-2">
                      <Lock className="w-4 h-4 text-blue-400" />
                      <span>Congelamiento Estructural</span>
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Al publicar la elección, se sella el <code>config_hash</code>. Cualquier intento de añadir candidatos o modificar cargos posteriores genera HTTP 409 Conflict (Invariante #3).
                    </p>
                  </div>

                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <h4 className="text-sm font-semibold text-white flex items-center space-x-2">
                      <Sparkles className="w-4 h-4 text-purple-400" />
                      <span>Arbitraje de Duplicados (IA-L2b)</span>
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      El modelo neuronal local audita casos limítrofes de homónimos en el padrón electoral, sugiriendo la acción óptima con justificación técnica.
                    </p>
                  </div>

                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <h4 className="text-sm font-semibold text-white flex items-center space-x-2">
                      <FileText className="w-4 h-4 text-emerald-400" />
                      <span>Informe Gemini y Actas Oficiales</span>
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Tras el escrutinio con quórum Shamir, genere el Informe Ejecutivo con Google Gemini 3.8 Flash (IA-E1) y descargue actas oficiales en PDF y Excel.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: CUSTODIOS SHAMIR */}
        {activeTab === 'trustee' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
                  <KeyRound className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Guía de Custodios Electorales — Protocolo de Quórum k de n</h2>
                  <p className="text-sm text-slate-400">
                    Procedimiento de resguardo de fragmentos secretos y apertura criptográfica de urnas al cierre de jornada.
                  </p>
                </div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-4 text-sm text-slate-300">
                <p>
                  Cada custodio representa a un estamento oficial (Comité Electoral, Docentes, Estudiantes, Notaría). Ningún custodio individual puede abrir la urna.
                </p>

                <div className="p-4 bg-amber-950/20 border border-amber-800/40 rounded-lg text-amber-200 space-y-2">
                  <div className="font-semibold flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>Formato Oficial del Fragmento</span>
                  </div>
                  <code className="block bg-slate-900 p-2.5 rounded font-mono text-xs text-amber-300 break-all">
                    SHAMIR-SHARE-v1-0002-0003-8f3a91b2c4e5...
                  </code>
                  <p className="text-xs">
                    Guarde este texto en un pendrive cifrado o sobre lacrado. Si se pierden más de $n - k$ fragmentos, la urna no podrá abrirse jamás.
                  </p>
                </div>

                <h3 className="font-semibold text-white pt-2">Ceremonia de Apertura al Cierre de Votación:</h3>
                <ol className="list-decimal list-inside space-y-2 text-slate-300">
                  <li>El Administrador General declara el cierre formal de urnas (<code>VOTING_CLOSED</code>).</li>
                  <li>Los custodios se presentan en la sala de cómputo o ingresan a la interfaz de ceremonia.</li>
                  <li>Cada custodio ingresa su fragmento secreto.</li>
                  <li>Al completarse el umbral de quórum $k$, el sistema reconstruye la clave en memoria volátil y ejecuta el escrutinio homomórfico aditivo.</li>
                </ol>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: DELEGADOS Y OBSERVADORES */}
        {activeTab === 'observer' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2.5 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
                  <Eye className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Manual de Delegados de Segmento y Observadores Públicos</h2>
                  <p className="text-sm text-slate-400">
                    Acceso sin credenciales al Portal Público de Auditoría y verificación independiente de sellos.
                  </p>
                </div>
              </div>

              <div className="space-y-4 text-sm text-slate-300">
                <p>
                  VotoSeguro implementa el principio de transparencia radical: cualquier ciudadano u observador internacional puede auditar la integridad del proceso en tiempo real sin requerir cuenta ni autorización previa.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <span className="text-xs font-mono text-cyan-400">ConfigHash & RollHash</span>
                    <p className="text-xs text-slate-300">
                      Garantizan que la lista de candidatos y el padrón de votantes habilitados no cambiaron un solo byte tras la publicación.
                    </p>
                  </div>

                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <span className="text-xs font-mono text-cyan-400">Ledger de Votos Encadenado</span>
                    <p className="text-xs text-slate-300">
                      Cada voto está ligado al hash del voto anterior formando una cadena inmutable con verificación instantánea de manipulaciones.
                    </p>
                  </div>

                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <span className="text-xs font-mono text-cyan-400">Historial del Cronograma</span>
                    <p className="text-xs text-slate-300">
                      Audite todas las ampliaciones o ajustes de horarios con fecha, responsable y motivo formal registrado en la bitácora.
                    </p>
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    to="/audit-portal"
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition"
                  >
                    <span>Abrir Portal de Auditoría Pública</span>
                    <ExternalLink className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: NODO NEURONAL LOCAL */}
        {activeTab === 'local_ai' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
                  <Cpu className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Operación del Nodo Neuronal Local (LFM-3b)</h2>
                  <p className="text-sm text-slate-400">
                    Puesta en marcha del modelo local calibrado con túnel seguro de ngrok para soberanía de datos.
                  </p>
                </div>
              </div>

              <div className="space-y-4 text-sm text-slate-300">
                <p>
                  El nodo neuronal local ejecuta el modelo <strong>Liquid-LFM-3b</strong> para tareas de privacidad estricta (OCR de cédula, liveness facial, arbitraje de duplicados y detección de anomalías en urnas).
                </p>

                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs space-y-3">
                  <div className="text-slate-400 flex items-center space-x-2">
                    <Terminal className="w-4 h-4 text-emerald-400" />
                    <span>Comando de Inicio Rápido en Windows:</span>
                  </div>
                  <div className="bg-slate-900 p-3 rounded text-emerald-300 select-all">
                    INICIAR_IA_LOCAL.bat
                  </div>
                  <p className="text-slate-400">
                    Este script verifica que LM Studio o vLLM estén ejecutándose en el puerto 1234, levanta el túnel ngrok y enlaza automáticamente el endpoint con el backend FastAPI.
                  </p>
                </div>

                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-white">Mecanismo de Respaldo Automático (Fallback)</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Si el nodo local se apaga o pierde conectividad temporalmente, el backend conmuta con cero interrupción hacia el analizador heurístico regex y el servicio de Google Gemini 3.8 Flash, garantizando disponibilidad continua durante el sufragio.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Pie de Página */}
      <footer className="border-t border-slate-800 bg-slate-900/60 py-6 text-center text-xs text-slate-500">
        <p>VotoSeguro v3.0.0 — Plataforma Electoral Universitaria Certificada con Criptografía Homomórfica e IA</p>
        <p className="mt-1">Facultad Integral del Chaco / FICCT — UAGRM 2026</p>
      </footer>
    </div>
  );
};

export default UserAndAdminManualPage;
