/**
 * Gramática Determinista Local para Comandos de Voz en Cabina Electoral (IA-L4).
 * REGLA CRÍTICA DE PRIVACIDAD (Sección 7.3):
 * 100% de procesamiento acústico e interpretación semántica en el dispositivo cliente.
 * JAMÁS envía transcripciones ni audios de la papeleta al backend ni al LLM.
 */

import { VoiceBallotAction, VoiceBallotCommand } from '@votoseguro/api-client';

const SPANISH_NUMBER_WORDS: Record<string, number> = {
  uno: 1,
  una: 1,
  primero: 1,
  primera: 1,
  dos: 2,
  segundo: 2,
  segunda: 2,
  tres: 3,
  tercero: 3,
  tercera: 3,
  cuatro: 4,
  cuarto: 4,
  cinco: 5,
  quinto: 5,
  seis: 6,
  sexto: 6,
  siete: 7,
  septimo: 7,
  ocho: 8,
  octavo: 8,
  nueve: 9,
  noveno: 9,
};

function normalizeTranscript(raw: string): string {
  if (!raw) return '';
  return raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[.,;:¿?¡!]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractNumber(text: string): number | null {
  // Buscar dígito 1-9
  const digitMatch = text.match(/\b([1-9])\b/);
  if (digitMatch) {
    return parseInt(digitMatch[1], 10);
  }

  // Buscar palabra en español
  const words = text.split(' ');
  for (const w of words) {
    if (SPANISH_NUMBER_WORDS[w] !== undefined) {
      return SPANISH_NUMBER_WORDS[w];
    }
  }

  return null;
}

export function parseVoiceBallotCommand(
  rawTranscript: string,
  currentContestCandidatesCount: number = 0
): VoiceBallotCommand {
  const norm = normalizeTranscript(rawTranscript);

  if (!norm) {
    return {
      action: 'UNKNOWN',
      rawTranscript,
      feedbackMessage: 'No se detectó ningún comando de voz reconocible.',
    };
  }

  // 1. Confirmación definitiva de emisión (Paso final de 2 pasos)
  if (
    norm.includes('confirmar emision definitiva') ||
    norm.includes('si confirmar voto') ||
    norm.includes('confirmar mi voto') ||
    norm === 'confirmar emision' ||
    norm === 'confirmar voto'
  ) {
    return {
      action: 'CONFIRM_CAST',
      rawTranscript,
      feedbackMessage: 'Confirmación definitiva reconocida. Depositando papeleta en la urna...',
    };
  }

  // 2. Preparar emisión de voto
  if (
    norm.includes('emitir voto') ||
    norm.includes('depositar papeleta') ||
    norm.includes('finalizar votacion') ||
    norm === 'emitir' ||
    norm === 'depositar'
  ) {
    return {
      action: 'PREPARE_CAST',
      rawTranscript,
      feedbackMessage: 'Preparando emisión. Diga "confirmar emisión definitiva" para depositar.',
    };
  }

  // 3. Leer resumen de selecciones
  if (
    norm.includes('leer resumen') ||
    norm.includes('verificar mi seleccion') ||
    norm.includes('que he marcado') ||
    norm.includes('revisar seleccion') ||
    norm === 'resumen'
  ) {
    return {
      action: 'READ_SUMMARY',
      rawTranscript,
      feedbackMessage: 'Leyendo el resumen completo de sus selecciones marcadas.',
    };
  }

  // 4. Voto en Blanco
  if (
    norm.includes('votar en blanco') ||
    norm.includes('voto en blanco') ||
    norm.includes('elegir blanco') ||
    norm === 'blanco'
  ) {
    return {
      action: 'SELECT_BLANK',
      rawTranscript,
      feedbackMessage: 'Opción Voto en Blanco seleccionada para este cargo.',
    };
  }

  // 5. Voto Nulo
  if (
    norm.includes('votar nulo') ||
    norm.includes('voto nulo') ||
    norm.includes('anular voto') ||
    norm === 'nulo' ||
    norm === 'anular'
  ) {
    return {
      action: 'SELECT_NULL',
      rawTranscript,
      feedbackMessage: 'Opción Voto Nulo seleccionada para este cargo.',
    };
  }

  // 6. Selección de Candidato específico por número o palabra
  if (
    norm.includes('candidato') ||
    norm.includes('opcion') ||
    norm.includes('votar por') ||
    norm.includes('elegir') ||
    norm.includes('seleccionar')
  ) {
    const candidateNum = extractNumber(norm);
    if (candidateNum !== null) {
      if (candidateNum >= 1 && candidateNum <= currentContestCandidatesCount) {
        return {
          action: 'SELECT_CANDIDATE',
          candidateNumber: candidateNum,
          rawTranscript,
          feedbackMessage: `Candidato número ${candidateNum} seleccionado.`,
        };
      } else {
        return {
          action: 'UNKNOWN',
          rawTranscript,
          feedbackMessage: `El candidato número ${candidateNum} no existe en este cargo (disponibles: 1 a ${currentContestCandidatesCount}).`,
        };
      }
    }
  }

  // 7. Navegación entre cargos: Siguiente
  if (
    norm.includes('siguiente cargo') ||
    norm.includes('siguiente') ||
    norm.includes('avanzar') ||
    norm.includes('proximo')
  ) {
    return {
      action: 'NEXT_CONTEST',
      rawTranscript,
      feedbackMessage: 'Avanzando al siguiente cargo de la papeleta.',
    };
  }

  // 8. Navegación entre cargos: Anterior
  if (
    norm.includes('cargo anterior') ||
    norm.includes('anterior') ||
    norm.includes('volver') ||
    norm.includes('atras')
  ) {
    return {
      action: 'PREV_CONTEST',
      rawTranscript,
      feedbackMessage: 'Retrocediendo al cargo anterior de la papeleta.',
    };
  }

  // 9. Leer papeleta / leer candidatos del cargo actual
  if (
    norm.includes('leer papeleta') ||
    norm.includes('leer cargo') ||
    norm.includes('quienes son los candidatos') ||
    norm.includes('leer opciones') ||
    norm.includes('opciones') ||
    norm.includes('repetir')
  ) {
    return {
      action: 'READ_BALLOT',
      rawTranscript,
      feedbackMessage: 'Leyendo las opciones disponibles para el cargo actual.',
    };
  }

  return {
    action: 'UNKNOWN',
    rawTranscript,
    feedbackMessage: `Comando "${rawTranscript}" no reconocido. Diga "leer opciones", "candidato uno", "voto en blanco" o "siguiente".`,
  };
}
