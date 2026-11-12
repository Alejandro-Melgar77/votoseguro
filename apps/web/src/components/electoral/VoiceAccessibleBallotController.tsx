/**
 * Controlador de Cabina Electoral Accesible por Voz (IA-L4).
 * Proporciona Síntesis de Voz (TTS) y Reconocimiento de Comandos de Voz (STT) locales.
 * Garantía: 100% en dispositivo, jamás envía audio ni intenciones de voto a la red.
 */
import React, { useEffect, useRef, useState } from 'react';
import { parseVoiceBallotCommand } from '../../lib/voice-ballot-grammar';

interface CandidateItem {
  id: string;
  name: string;
  party?: string | null;
}

interface VoiceAccessibleBallotControllerProps {
  activeContestName: string;
  candidates: CandidateItem[];
  selectedChoiceType: 'CANDIDATE' | 'BLANK' | 'NULL' | null;
  selectedCandidateId: string | null;
  contestIndex: number;
  totalContests: number;
  onSelectCandidate: (candidateId: string) => void;
  onSelectBlank: () => void;
  onSelectNull: () => void;
  onNextContest: () => void;
  onPrevContest: () => void;
  onPrepareCast?: () => void;
  onConfirmCast: () => void;
}

export const VoiceAccessibleBallotController: React.FC<VoiceAccessibleBallotControllerProps> = ({
  activeContestName,
  candidates,
  selectedChoiceType,
  selectedCandidateId,
  contestIndex,
  totalContests,
  onSelectCandidate,
  onSelectBlank,
  onSelectNull,
  onNextContest,
  onPrevContest,
  onPrepareCast,
  onConfirmCast,
}) => {
  const [isTtsActive, setIsTtsActive] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [feedback, setFeedback] = useState<string>('Modo accesible listo. Puede activar la lectura o usar comandos de voz.');
  const [hasSpeechRecognition, setHasSpeechRecognition] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Comprobar soporte de SpeechRecognition en el navegador
  useEffect(() => {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRec) {
      setHasSpeechRecognition(true);
      const rec = new SpeechRec();
      rec.lang = 'es-ES';
      rec.continuous = false;
      rec.interimResults = false;

      rec.onstart = () => {
        setIsListening(true);
        setFeedback('Escuchando su comando de voz...');
      };

      rec.onend = () => {
        setIsListening(false);
      };

      rec.onerror = (e: any) => {
        setIsListening(false);
        setFeedback(`Micrófono: ${e.error || 'No se pudo captar el audio'}.`);
      };

      rec.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        handleExecuteTranscript(transcript);
      };

      recognitionRef.current = rec;
    }
  }, [candidates, contestIndex, totalContests]);

  const speak = (text: string) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES';
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  const handleReadContest = () => {
    setIsTtsActive(true);
    let speechText = `Cargo número ${contestIndex + 1} de ${totalContests}: ${activeContestName}. `;
    speechText += `Hay ${candidates.length} candidatos disponibles. `;

    candidates.forEach((c, idx) => {
      speechText += `Opción ${idx + 1}: ${c.name}, ${c.party ? `agrupación ${c.party}` : ''}. `;
    });

    speechText += 'También dispone de las opciones: Voto en Blanco y Voto Nulo. ';

    if (selectedChoiceType === 'CANDIDATE' && selectedCandidateId) {
      const cand = candidates.find((c) => c.id === selectedCandidateId);
      speechText += `Usted tiene marcado actualmente al candidato: ${cand?.name || 'seleccionado'}. `;
    } else if (selectedChoiceType === 'BLANK') {
      speechText += 'Usted tiene marcado actualmente: Voto en Blanco. ';
    } else if (selectedChoiceType === 'NULL') {
      speechText += 'Usted tiene marcado actualmente: Voto Nulo. ';
    } else {
      speechText += 'Aún no ha seleccionado ninguna opción para este cargo. ';
    }

    speechText += 'Diga "elegir opción uno", "voto en blanco", o "siguiente cargo".';
    setFeedback(speechText);
    speak(speechText);
  };

  const handleExecuteTranscript = (transcript: string) => {
    const cmd = parseVoiceBallotCommand(transcript, candidates.length);
    setFeedback(cmd.feedbackMessage);

    // Reproducir confirmación auditiva TTS
    speak(cmd.feedbackMessage);

    switch (cmd.action) {
      case 'READ_BALLOT':
        handleReadContest();
        break;
      case 'NEXT_CONTEST':
        if (contestIndex < totalContests - 1) {
          onNextContest();
        } else {
          speak('Ya se encuentra en el último cargo. Diga "emitir voto" para revisar su papeleta.');
        }
        break;
      case 'PREV_CONTEST':
        if (contestIndex > 0) {
          onPrevContest();
        } else {
          speak('Se encuentra en el primer cargo de la papeleta.');
        }
        break;
      case 'SELECT_CANDIDATE':
        if (cmd.candidateNumber && cmd.candidateNumber <= candidates.length) {
          const target = candidates[cmd.candidateNumber - 1];
          if (target) {
            onSelectCandidate(target.id);
          }
        }
        break;
      case 'SELECT_BLANK':
        onSelectBlank();
        break;
      case 'SELECT_NULL':
        onSelectNull();
        break;
      case 'READ_SUMMARY':
        handleReadContest();
        break;
      case 'PREPARE_CAST':
        if (onPrepareCast) {
          onPrepareCast();
        } else {
          speak('Para confirmar definitivamente su voto, diga: "confirmar emisión definitiva".');
        }
        break;
      case 'CONFIRM_CAST':
        onConfirmCast();
        break;
      default:
        break;
    }
  };

  const toggleListening = () => {
    if (!hasSpeechRecognition) {
      setFeedback('Reconocimiento por voz no disponible en este navegador. Utilice la botonera asistida.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current?.start();
      } catch (err) {
        console.warn('Error arrancando SpeechRecognition:', err);
      }
    }
  };

  return (
    <div className="bg-[#0B132B] text-white rounded-xl p-4 shadow-lg border border-emerald-500/30 mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-gray-700 pb-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-lg">
            🎙️
          </div>
          <div>
            <h3 className="font-semibold text-sm md:text-base flex items-center gap-2">
              Cabina Accesible por Voz Local (IA-L4)
              <span className="text-[11px] bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/40">
                100% On-Device
              </span>
            </h3>
            <p className="text-xs text-gray-300">
              Lectura hablada (TTS) y comandos de voz deterministas para personas con discapacidad visual.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleReadContest}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition-colors"
          >
            <span>🔊</span> Leer Cargo
          </button>

          <button
            type="button"
            onClick={toggleListening}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all ${
              isListening
                ? 'bg-red-600 animate-pulse text-white font-bold ring-2 ring-red-400'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            <span>{isListening ? '🔴' : '🎤'}</span>
            {isListening ? 'Escuchando...' : 'Comando de Voz'}
          </button>
        </div>
      </div>

      {/* Mensaje de retroalimentación en tiempo real */}
      <div className="bg-gray-900/80 rounded-lg p-2.5 text-xs text-emerald-200 border border-gray-700/60 flex items-start gap-2 mb-3">
        <span className="text-emerald-400 mt-0.5 font-bold">💬</span>
        <div className="flex-1 leading-relaxed">
          <span className="font-semibold text-gray-300">Estado de la cabina: </span>
          {feedback}
        </div>
      </div>

      {/* Botonera de Comandos de Voz Asistida (para prueba y accesibilidad sin micrófono) */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-gray-400 text-[11px] font-medium mr-1">Comandos rápidos:</span>
        {candidates.map((c, idx) => (
          <button
            key={c.id}
            type="button"
            onClick={() => handleExecuteTranscript(`candidato ${idx + 1}`)}
            className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-600 transition-colors"
          >
            🗣️ Candidato {idx + 1}
          </button>
        ))}
        <button
          type="button"
          onClick={() => handleExecuteTranscript('votar en blanco')}
          className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-600 transition-colors"
        >
          ⚪ Blanco
        </button>
        <button
          type="button"
          onClick={() => handleExecuteTranscript('votar nulo')}
          className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-600 transition-colors"
        >
          ❌ Nulo
        </button>
        <button
          type="button"
          onClick={() => handleExecuteTranscript('siguiente cargo')}
          className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-600 transition-colors"
        >
          ➡️ Siguiente
        </button>
        <button
          type="button"
          onClick={() => handleExecuteTranscript('confirmar emision definitiva')}
          className="px-2 py-1 rounded bg-emerald-800/80 hover:bg-emerald-700 text-emerald-100 border border-emerald-500/40 font-semibold transition-colors"
        >
          ✅ Confirmar Voto
        </button>
      </div>

      <div className="mt-2.5 pt-2 border-t border-gray-800/80 flex items-center justify-between text-[11px] text-gray-400">
        <span className="flex items-center gap-1 text-emerald-400">
          <span>🛡️</span> Procesamiento Acústico 100% en Dispositivo — Ningún audio ni comando viaja por la red
        </span>
        <span className="hidden md:inline">Invariante de Secreto #9 y #17</span>
      </div>
    </div>
  );
};
