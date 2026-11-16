import React, { useState, useEffect } from 'react';
import {
  FileText,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Printer,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api';

interface ExecutiveReportItem {
  id: string;
  organization_id: string;
  election_id: string;
  language: string;
  model_used: string;
  ai_source: string;
  title: string;
  summary_markdown: string;
  key_highlights: string[];
  integrity_certification: string;
  recommendations: string[];
  report_hash: string;
  created_at: string;
}

interface ExecutiveReportGeneratorCardProps {
  electionId: string;
  electionName?: string;
  isVotingClosed?: boolean;
}

export const ExecutiveReportGeneratorCard: React.FC<ExecutiveReportGeneratorCardProps> = ({
  electionId,
  electionName,
  isVotingClosed = false,
}) => {
  const [tone, setTone] = useState<'FORMAL_COURT' | 'EXECUTIVE_BRIEF'>('FORMAL_COURT');
  const [loading, setLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentReport, setCurrentReport] = useState<ExecutiveReportItem | null>(null);
  const [historicalReports, setHistoricalReports] = useState<ExecutiveReportItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchReports = async () => {
    if (!electionId) return;
    setFetchingHistory(true);
    try {
      const data = await api.get<ExecutiveReportItem[]>(`/ai/reports/executive/${electionId}`);
      setHistoricalReports(data || []);
      if (data && data.length > 0 && !currentReport) {
        setCurrentReport(data[0]);
      }
    } catch (err: any) {
      console.warn('No se pudo cargar historial de informes ejecutivos:', err);
    } finally {
      setFetchingHistory(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [electionId]);

  const handleGenerateReport = async () => {
    if (!electionId) return;
    setLoading(true);
    setError(null);
    try {
      const newReport = await api.post<ExecutiveReportItem>(`/ai/reports/executive`, {
        election_id: electionId,
        tone: tone,
      });
      setCurrentReport(newReport);
      setHistoricalReports((prev) => [newReport, ...prev]);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Error al redactar el informe ejecutivo oficial con Gemini API.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMarkdown = () => {
    if (!currentReport) return;
    const content = `
# ${currentReport.title}
**Sello SHA-256:** \`${currentReport.report_hash}\`  
**Motor IA:** ${currentReport.model_used} (${currentReport.ai_source})  
**Fecha de Emisión:** ${new Date(currentReport.created_at).toLocaleString()}  

---

${currentReport.summary_markdown}

---

### Certificación de Integridad Criptográfica
${currentReport.integrity_certification}

---

### Puntos Clave
${currentReport.key_highlights.map((h) => `- ${h}`).join('\n')}

---

### Recomendaciones Institucionales
${currentReport.recommendations.map((r) => `- ${r}`).join('\n')}
`.trim();

    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden space-y-0">
      {/* Cabecera del Panel */}
      <div className="bg-gradient-to-r from-civic-navy-950 via-civic-navy-900 to-stone-900 text-white p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-bold font-serif tracking-tight text-white">
              Informe Ejecutivo en Lenguaje Natural con Gemini (IA-E1)
            </h3>
          </div>
          <p className="text-xs text-stone-300">
            Redacción asistida para la Corte Electoral basada <strong>exclusivamente en métricas agregadas</strong> (Invariante #14).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value as any)}
            className="px-3 py-1.5 rounded-lg bg-stone-800 border border-stone-700 text-xs font-medium text-stone-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
          >
            <option value="FORMAL_COURT">Tono: Acta Formal de Corte Electoral</option>
            <option value="EXECUTIVE_BRIEF">Tono: Resumen Ejecutivo Directo</option>
          </select>

          <button
            onClick={handleGenerateReport}
            disabled={loading}
            className="px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:bg-stone-700 text-stone-950 font-bold text-xs flex items-center gap-2 shadow-sm transition-all"
          >
            <Sparkles className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Redactando con Gemini...' : 'Redactar Informe Oficial'}
          </button>
        </div>
      </div>

      {/* Alerta de Privacidad Estricta */}
      <div className="bg-emerald-50/80 border-b border-emerald-100 px-5 py-2.5 flex items-center justify-between text-xs text-emerald-900">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>
            <strong>Garantía de Privacidad Cívica (Invariante #14):</strong> Este informe se construye
            únicamente con totales de participación, cronograma y sellos de integridad. Cero CIs, nombres o votos individuales enviados.
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 mx-5 my-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {/* Visualizador de Informe */}
      {currentReport ? (
        <div className="p-6 space-y-6">
          <div className="border border-stone-200 rounded-xl p-6 bg-stone-50/40 space-y-5 print:border-none print:p-0">
            {/* Meta y Badges */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-4">
              <div className="space-y-1">
                <span className="text-[10px] font-mono uppercase tracking-widest text-stone-400">
                  Acta Oficial Institucional
                </span>
                <h4 className="text-xl font-bold font-serif text-stone-900">{currentReport.title}</h4>
                <p className="text-xs text-stone-500">
                  Emitido el {new Date(currentReport.created_at).toLocaleString()}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-stone-100 text-stone-700 border border-stone-200">
                  {currentReport.model_used}
                </span>
                <span
                  className={`px-2.5 py-1 rounded-md text-[11px] font-bold ${
                    currentReport.ai_source === 'GEMINI_EXTERNAL_API'
                      ? 'bg-purple-100 text-purple-800 border border-purple-200'
                      : 'bg-amber-100 text-amber-800 border border-amber-200'
                  }`}
                >
                  {currentReport.ai_source}
                </span>
              </div>
            </div>

            {/* Sello de Integridad del Informe */}
            <div className="p-2.5 bg-stone-900 text-stone-300 rounded-lg font-mono text-[11px] flex items-center justify-between gap-2 overflow-x-auto">
              <span className="text-stone-400">Sello SHA-256 del Informe:</span>
              <span className="text-emerald-400 font-semibold">{currentReport.report_hash}</span>
            </div>

            {/* Cuerpo del Informe */}
            <div className="prose prose-sm max-w-none text-stone-800 space-y-4 leading-relaxed">
              <div className="whitespace-pre-wrap font-sans text-xs sm:text-sm">
                {currentReport.summary_markdown}
              </div>

              <div className="bg-white border border-stone-200 rounded-xl p-4 space-y-2">
                <h5 className="font-bold text-xs uppercase tracking-wide text-civic-navy-950 flex items-center gap-1.5 font-mono">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Certificación de Integridad y Sellos Criptográficos
                </h5>
                <p className="text-xs text-stone-700 whitespace-pre-wrap">
                  {currentReport.integrity_certification}
                </p>
              </div>

              {currentReport.key_highlights?.length > 0 && (
                <div className="space-y-1.5">
                  <h5 className="font-bold text-xs uppercase tracking-wide text-stone-700">Puntos Clave</h5>
                  <ul className="list-disc pl-5 space-y-1 text-xs text-stone-700">
                    {currentReport.key_highlights.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                </div>
              )}

              {currentReport.recommendations?.length > 0 && (
                <div className="space-y-1.5">
                  <h5 className="font-bold text-xs uppercase tracking-wide text-stone-700">
                    Recomendaciones Institucionales
                  </h5>
                  <ul className="list-disc pl-5 space-y-1 text-xs text-stone-700">
                    {currentReport.recommendations.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Acciones */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-stone-200 print:hidden">
              <button
                onClick={handleCopyMarkdown}
                className="px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-stone-50 text-xs font-semibold text-stone-700 flex items-center gap-1.5 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" /> Copiado
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" /> Copiar Markdown
                  </>
                )}
              </button>

              <button
                onClick={handlePrint}
                className="px-3 py-1.5 rounded-lg bg-civic-navy-950 hover:bg-civic-navy-900 text-xs font-semibold text-white flex items-center gap-1.5 transition-colors"
              >
                <Printer className="w-3.5 h-3.5" /> Imprimir Acta
              </button>
            </div>
          </div>

          {/* Historial de Informes */}
          {historicalReports.length > 1 && (
            <div className="border border-stone-200 rounded-xl overflow-hidden text-xs">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="w-full px-4 py-2.5 bg-stone-50 hover:bg-stone-100 flex items-center justify-between text-stone-700 font-semibold"
              >
                <span>Historial de Informes Ejecutivos Emitidos ({historicalReports.length})</span>
                {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showHistory && (
                <div className="divide-y divide-stone-100 bg-white max-h-48 overflow-y-auto">
                  {historicalReports.map((rep) => (
                    <button
                      key={rep.id}
                      onClick={() => setCurrentReport(rep)}
                      className={`w-full text-left p-3 hover:bg-stone-50 transition-colors flex items-center justify-between ${
                        currentReport.id === rep.id ? 'bg-amber-50/50 font-bold' : ''
                      }`}
                    >
                      <div>
                        <p className="text-stone-900">{rep.title}</p>
                        <p className="text-[10px] text-stone-400 font-mono">
                          {new Date(rep.created_at).toLocaleString()} • {rep.ai_source}
                        </p>
                      </div>
                      <span className="text-[10px] font-mono text-stone-500">
                        {rep.report_hash.substring(0, 10)}...
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-stone-500 space-y-2">
          <FileText className="w-8 h-8 text-stone-300 mx-auto" />
          <p className="font-semibold text-stone-700">Aún no se ha redactado ningún informe ejecutivo</p>
          <p>Haga clic en "Redactar Informe Oficial" para generar el primer informe asistido por Gemini.</p>
        </div>
      )}
    </div>
  );
};
