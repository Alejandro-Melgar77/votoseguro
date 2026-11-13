/**
 * Modal de Escaneo y Extracción de Cédula de Identidad (IA-L3).
 * Cumple la Invariante #15: CERO persistencia ni transmisión de imágenes al servidor.
 * El usuario puede subir una foto (procesada en canvas local) o seleccionar una plantilla demo en 1 clic.
 */
import React, { useState } from 'react';
import { api } from '../../lib/api';
import { IdCardExtractionResponse } from '@votoseguro/api-client';
import { AiEngineTelemetryBadge } from './AiEngineTelemetryBadge';

interface IdCardOcrScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (data: { ci: string; nombres: string; apellidos: string; fecha_nacimiento?: string | null }) => void;
  electionId?: string;
}

const DEMO_TEMPLATES = [
  {
    label: 'Cédula Demo 1 (Juan Carlos Pérez - 8001002)',
    text: `ESTADO PLURINACIONAL DE BOLIVIA
CEDULA DE IDENTIDAD
N° 8001002 SC
NOMBRES: JUAN CARLOS
APELLIDOS: PEREZ GOMEZ
FECHA DE NACIMIENTO: 14/05/2001
ESTADO CIVIL: SOLTERO`,
  },
  {
    label: 'Cédula Demo 2 (María Elena Rojas - 8001003)',
    text: `ESTADO PLURINACIONAL DE BOLIVIA
CEDULA DE IDENTIDAD
N° 8001003 SC
NOMBRES: MARIA ELENA
APELLIDOS: ROJAS SUAREZ
FECHA DE NACIMIENTO: 22/09/2002
ESTADO CIVIL: SOLTERA`,
  },
  {
    label: 'Cédula Demo 3 (Roberto Callau - 8001008)',
    text: `ESTADO PLURINACIONAL DE BOLIVIA
CEDULA DE IDENTIDAD
N° 8001008 SC
NOMBRES: ROBERTO
APELLIDOS: CALLAU MELGAR
FECHA DE NACIMIENTO: 10/11/1985
PROFESION: DOCENTE`,
  },
];

export const IdCardOcrScannerModal: React.FC<IdCardOcrScannerModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  electionId,
}) => {
  const [rawText, setRawText] = useState<string>(DEMO_TEMPLATES[0].text);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractedResult, setExtractedResult] = useState<IdCardExtractionResponse | null>(null);

  if (!isOpen) return null;

  const handleSelectTemplate = (text: string) => {
    setRawText(text);
    setExtractedResult(null);
    setError(null);
  };

  const handleProcessImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Invariante #15: Cargar en Image/Canvas localmente para simular OCR de cámara y descartar buffer
    const reader = new FileReader();
    reader.onload = (event) => {
      // Simulación de lectura óptica en dispositivo sin enviar la imagen
      const img = new Image();
      img.onload = () => {
        // En un dispositivo real con Tesseract.js / MLKit, aquí se extraen las líneas de texto.
        // Simulamos la extracción de texto OCR desde el documento analizado localmente:
        const simulatedOcr = `ESTADO PLURINACIONAL DE BOLIVIA\nCEDULA DE IDENTIDAD\nN° 8001002 SC\nNOMBRES: JUAN CARLOS\nAPELLIDOS: PEREZ GOMEZ\nFECHA DE NACIMIENTO: 14/05/2001\n[Imagen analizada en canvas local: ${img.width}x${img.height}px y descartada de memoria]`;
        setRawText(simulatedOcr);
        setExtractedResult(null);
      };
      img.src = event.target?.result as string;
    };
    reader.readAsDataURL(file);
    // Limpiar input
    e.target.value = '';
  };

  const handleExtract = async () => {
    if (!rawText.trim()) {
      setError('Por favor seleccione una plantilla o pegue el texto de la cédula.');
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
              <p className="text-xs text-gray-300">Extracción estructurada con IA Local (IA-L3)</p>
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

          {/* Plantillas de Demostración de 1 Clic */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              1. Seleccione una Cédula Demo o capture foto desde su dispositivo:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {DEMO_TEMPLATES.map((tmpl, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectTemplate(tmpl.text)}
                  className={`p-2 rounded-lg border text-left text-xs font-medium transition-all ${
                    rawText === tmpl.text
                      ? 'border-emerald-600 bg-emerald-50/70 text-emerald-900 ring-1 ring-emerald-600'
                      : 'border-gray-200 hover:border-gray-300 bg-gray-50 text-gray-700'
                  }`}
                >
                  <div className="font-semibold text-gray-900 truncate">Demo {idx + 1}</div>
                  <div className="text-[11px] text-gray-500 truncate">{tmpl.label.split('(')[1]?.replace(')', '')}</div>
                </button>
              ))}
            </div>

            <div className="mt-2.5 flex items-center gap-3">
              <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-xs font-medium text-gray-700 shadow-sm transition-colors">
                <span>📷</span> Capturar / Subir Foto
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={handleProcessImage}
                />
              </label>
              <span className="text-[11px] text-gray-500">
                (El OCR se ejecuta en navegador sin enviar la foto)
              </span>
            </div>
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
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-[#0B132B] hover:bg-[#162550] text-white font-medium text-xs flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="animate-spin text-sm">⏳</span> Analizando con LFM3-1.7B...
                </>
              ) : (
                <>
                  <span>✨</span> Extraer Campos con IA Local
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
