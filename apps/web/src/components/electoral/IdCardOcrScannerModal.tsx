/**
 * Modal de Escaneo y Extracción de Cédula de Identidad (IA-L3).
 * Cumple la Invariante #15: CERO persistencia ni transmisión de imágenes al servidor.
 * Lee fotografías con Tesseract en el dispositivo. Solo se envía texto confirmado para extraer campos.
 */
import React, { useEffect, useRef, useState } from 'react';
import { recognizeIdCard } from '../../lib/id-card-ocr';
import { api } from '../../lib/api';
import { IdCardExtractionResponse } from '@votoseguro/api-client';
import { AiEngineTelemetryBadge } from './AiEngineTelemetryBadge';

interface IdCardOcrScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (data: { ci: string; nombres: string; apellidos: string; fecha_nacimiento?: string | null }) => void;
  electionId?: string;
}


export const IdCardOcrScannerModal: React.FC<IdCardOcrScannerModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  electionId,
}) => {
  const [rawText, setRawText] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractedResult, setExtractedResult] = useState<IdCardExtractionResponse | null>(null);

  const [ocrProgress, setOcrProgress] = useState<number | null>(null);
  const scanId = useRef(0);
  useEffect(() => {
    if (!isOpen) { scanId.current++; setRawText(''); setExtractedResult(null); setError(null); setOcrProgress(null); }
  }, [isOpen]);
  useEffect(() => () => { scanId.current++; }, []);
  if (!isOpen) return null;

  const handleProcessImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const id = ++scanId.current;
    setError(null); setRawText(''); setExtractedResult(null); setOcrProgress(0);
    try {
      const text = await recognizeIdCard(file, value => { if (scanId.current === id) setOcrProgress(value); });
      if (scanId.current === id) setRawText(text);
    } catch (err) {
      if (scanId.current === id) setError(err instanceof Error ? err.message : 'No se pudo leer la foto.');
    } finally { if (scanId.current === id) setOcrProgress(null); }
  };

  const handleExtract = async () => {
    if (!rawText.trim()) {
      setError('Fotografíe la cédula o pegue el texto que desea revisar.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await api.post<IdCardExtractionResponse>('/ai/id-card/extract', {
        raw_ocr_text: rawText,
        election_id: electionId || null,
      });
      setExtractedResult(response);
    } catch (err: any) {
      setError(err.message || 'Error al procesar el texto OCR de la cédula.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAndApply = () => {
    if (!extractedResult) return;
    onConfirm({
      ci: extractedResult.ci,
      nombres: extractedResult.nombres,
      apellidos: extractedResult.apellidos,
      fecha_nacimiento: extractedResult.fecha_nacimiento,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-gray-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Encabezado */}
        <div className="bg-[#0B132B] text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-lg">
              🪪
            </div>
            <div>
              <h3 className="font-bold text-base">Escaneo OCR de Cédula de Identidad</h3>
              <p className="text-xs text-gray-300">Lectura en su dispositivo y extracción asistida por IA</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg font-bold p-1 rounded-lg transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Cuerpo */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm text-gray-700">
          {/* Banner de Privacidad Invariante #15 */}
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-2.5 text-xs text-emerald-900">
            <span className="text-base text-emerald-700">🔒</span>
            <div className="leading-relaxed">
              <strong className="font-semibold">Privacidad garantizada (Invariante #15):</strong> La imagen de su
              documento se procesa exclusivamente en su dispositivo y es descartada de la memoria. Ninguna foto ni
              binario se almacena en el servidor.
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold mb-2">Fotografíe la cédula completa, con buena luz y sin reflejos.</label>
            <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
              aria-label="Fotografía de la cédula" disabled={ocrProgress !== null || loading} onChange={handleProcessImage} />
            {ocrProgress !== null && <p role="status">Leyendo documento: {Math.round(ocrProgress * 100)} %</p>}
            <p className="text-xs mt-2">La foto se lee en este dispositivo. Revise el texto antes de extraer los campos.</p>
          </div>

          {/* Texto OCR Bruto */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              2. Texto OCR detectado en el documento:
            </label>
            <textarea
              rows={4}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              className="w-full font-mono text-xs p-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              placeholder="El texto OCR aparecerá aquí..."
            />
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleExtract}
              disabled={loading || ocrProgress !== null || !rawText.trim()}
              className="px-4 py-2 rounded-xl bg-[#0B132B] hover:bg-[#162550] text-white font-medium text-xs flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="animate-spin text-sm">⏳</span> Extrayendo los campos...
                </>
              ) : (
                <>
                  <span>✨</span> Extraer Campos con IA
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
              {error}
            </div>
          )}

          {/* Tarjeta de Resultados Extraídos */}
          {extractedResult && (
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-3">
              <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                <span className="font-semibold text-xs text-gray-900 flex items-center gap-1.5">
                  <span>✅</span> Campos Extraídos del Documento
                </span>
                <span
                  className={`text-[11px] px-2 py-0.5 rounded font-medium ${
                    extractedResult.regex_valid
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {extractedResult.regex_valid ? 'Regex Válido' : 'Revisión Sugerida'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500 block text-[11px]">Cédula de Identidad (CI):</span>
                  <strong className="text-gray-900 font-mono text-sm">{extractedResult.ci}</strong>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Fecha de Nacimiento:</span>
                  <span className="text-gray-900 font-medium">
                    {extractedResult.fecha_nacimiento || 'No detectada'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Nombres:</span>
                  <span className="text-gray-900 font-medium">{extractedResult.nombres}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Apellidos:</span>
                  <span className="text-gray-900 font-medium">{extractedResult.apellidos}</span>
                </div>
              </div>

              <div className="text-[11px] text-gray-500 italic">
                {extractedResult.confidence_note}
              </div>

              <div className="pt-2 border-t border-gray-200 flex items-center justify-between">
                <AiEngineTelemetryBadge
                  source={extractedResult.ai_source}
                  modelName={extractedResult.model_name}
                  latencyMs={extractedResult.latency_ms}
                />
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-gray-200">
                <button
                  type="button"
                  onClick={handleConfirmAndApply}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center gap-1.5 shadow-sm transition-colors"
                >
                  <span>✓</span> Confirmar mis datos y rellenar formulario
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
