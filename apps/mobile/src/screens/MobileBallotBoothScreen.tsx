import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { mobileApi, setMobileAuthToken, getMobileAuthToken } from '../api/mobile-client';
import {
  VoterLoginRequest,
  VoterSessionResponse,
  AutomaticBallotResponse,
  ContestBallotItem,
  CandidateBallotItem,
  CastReceiptResponse,
  VoteSelectionItem,
} from '@votoseguro/api-client';
import { parseMobileVoiceBallotCommand } from '../lib/voice-ballot-grammar';

interface MobileBallotBoothScreenProps {
  onNavigate: (screen: 'home' | 'register' | 'booth' | 'receipt' | 'faq', params?: any) => void;
}

interface SelectedVote {
  choiceType: 'CANDIDATE' | 'BLANK' | 'NULL';
  candidateId?: string | null;
  candidateName?: string;
  candidateNumber?: number;
}

export const MobileBallotBoothScreen: React.FC<MobileBallotBoothScreenProps> = ({ onNavigate }) => {
  // Estado de flujo de la cabina
  const [step, setStep] = useState<'login' | 'ballot' | 'confirm' | 'receipt'>('login');

  // Login
  const [documentId, setDocumentId] = useState('');
  const [credentialCode, setCredentialCode] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Papeleta
  const [ballot, setBallot] = useState<AutomaticBallotResponse | null>(null);
  const [ballotLoading, setBallotLoading] = useState(false);
  const [currentContestIdx, setCurrentContestIdx] = useState(0);
  const [selections, setSelections] = useState<Record<string, SelectedVote>>({});

  // Accesibilidad por Voz (IA-L4)
  const [voiceModeActive, setVoiceModeActive] = useState(false);
  const [spokenFeedback, setSpokenFeedback] = useState<string | null>(null);
  const [voiceCommandInput, setVoiceCommandInput] = useState('');

  // Emisión y Comprobante
  const [castLoading, setCastLoading] = useState(false);
  const [castError, setCastError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<CastReceiptResponse | null>(null);

  // Comprobar si ya existe token de sesión
  useEffect(() => {
    if (getMobileAuthToken() && !ballot) {
      loadBallot();
    }
  }, []);

  const handleLogin = async () => {
    if (!documentId.trim() || !credentialCode.trim()) {
      setLoginError('Ingrese su número de documento (CI) y la credencial de votación.');
      return;
    }

    setLoginLoading(true);
    setLoginError(null);

    try {
      const res = await mobileApi.post<VoterSessionResponse>('/voter/login', {
        document_id: documentId.trim(),
        credential_code: credentialCode.trim().toUpperCase(),
      });

      setMobileAuthToken(res.access_token);
      await loadBallot();
    } catch (err: any) {
      setLoginError(err.message || 'Error al iniciar sesión en la cabina de votación.');
    } finally {
      setLoginLoading(false);
    }
  };

  const loadBallot = async () => {
    setBallotLoading(true);
    try {
      const data = await mobileApi.get<AutomaticBallotResponse>('/ballot');
      setBallot(data);
      setCurrentContestIdx(0);
      setStep('ballot');

      if (voiceModeActive) {
        speak(
          `Bienvenido a la cabina electoral accesible. Elección: ${data.election_name}. Contiene ${data.contests.length} cargos a sufragar. Diga "leer papeleta" para escuchar los candidatos del primer cargo.`
        );
      }
    } catch (err: any) {
      setLoginError(err.message || 'No se pudo cargar la papeleta oficial asignada a su estamento.');
      setStep('login');
    } finally {
      setBallotLoading(false);
    }
  };

  const currentContest: ContestBallotItem | undefined = ballot?.contests[currentContestIdx];

  const speak = (message: string) => {
    setSpokenFeedback(message);
  };

  // Manejador del motor de gramática de voz (IA-L4)
  const handleVoiceCommand = (commandText: string) => {
    if (!commandText.trim()) return;

    const candidatesCount = currentContest?.candidates?.length || 0;
    const parsed = parseMobileVoiceBallotCommand(commandText, candidatesCount);

    speak(parsed.feedbackMessage);

    switch (parsed.action) {
      case 'READ_BALLOT':
        if (currentContest) {
          const candList = currentContest.candidates
            .map((c, i) => `Opción ${i + 1}: ${c.name}, ${c.party_or_front || 'Independiente'}`)
            .join('. ');
          speak(
            `Cargo actual: ${currentContest.contest_name}. Candidatos: ${candList}. También puede decir "voto en blanco" o "voto nulo".`
          );
        }
        break;

      case 'SELECT_CANDIDATE':
        if (currentContest && parsed.candidateNumber) {
          const cand = currentContest.candidates[parsed.candidateNumber - 1];
          if (cand) {
            setSelections((prev) => ({
              ...prev,
              [currentContest.contest_id]: {
                choiceType: 'CANDIDATE',
                candidateId: cand.id,
                candidateName: cand.name,
                candidateNumber: parsed.candidateNumber,
              },
            }));
            speak(
              `Ha seleccionado al candidato número ${parsed.candidateNumber}: ${cand.name}. Diga "siguiente cargo" o "emitir voto" cuando termine.`
            );
          }
        }
        break;

      case 'SELECT_BLANK':
        if (currentContest) {
          setSelections((prev) => ({
            ...prev,
            [currentContest.contest_id]: {
              choiceType: 'BLANK',
              candidateName: 'VOTO EN BLANCO',
            },
          }));
          speak(`Ha seleccionado Voto en Blanco para ${currentContest.contest_name}.`);
        }
        break;

      case 'SELECT_NULL':
        if (currentContest) {
          setSelections((prev) => ({
            ...prev,
            [currentContest.contest_id]: {
              choiceType: 'NULL',
              candidateName: 'VOTO NULO',
            },
          }));
          speak(`Ha seleccionado Voto Nulo para ${currentContest.contest_name}.`);
        }
        break;

      case 'NEXT_CONTEST':
        if (ballot && currentContestIdx < ballot.contests.length - 1) {
          const nextIdx = currentContestIdx + 1;
          setCurrentContestIdx(nextIdx);
          speak(
            `Avanzando al siguiente cargo: ${ballot.contests[nextIdx].contest_name}. Diga "leer papeleta" para escuchar las opciones.`
          );
        } else {
          speak('Ya se encuentra en el último cargo de la papeleta. Diga "emitir voto" para continuar a la confirmación.');
        }
        break;

      case 'PREV_CONTEST':
      case 'PREVIOUS_CONTEST':
        if (ballot && currentContestIdx > 0) {
          const prevIdx = currentContestIdx - 1;
          setCurrentContestIdx(prevIdx);
          speak(`Volviendo al cargo anterior: ${ballot.contests[prevIdx].contest_name}.`);
        } else {
          speak('Se encuentra en el primer cargo de la papeleta.');
        }
        break;

      case 'CANCEL':
      case 'CANCEL_SELECTION':
        if (currentContest) {
          setSelections((prev) => {
            const copy = { ...prev };
            delete copy[currentContest.contest_id];
            return copy;
          });
          speak(`Selección desmarcada para el cargo ${currentContest.contest_name}.`);
        }
        break;

      case 'READ_SUMMARY':
        if (ballot) {
          const summary = ballot.contests
            .map((c) => {
              const sel = selections[c.contest_id];
              const text = sel ? sel.candidateName : 'Sin selección';
              return `${c.contest_name}: ${text}`;
            })
            .join('. ');
          speak(`Resumen de su papeleta: ${summary}. Diga "emitir voto" para confirmar.`);
        }
        break;

      case 'PREPARE_CAST':
        setStep('confirm');
        speak(
          'Ha ingresado al paso de confirmación. Revise sus opciones. Diga "confirmar emisión definitiva" para depositar la papeleta en la urna.'
        );
        break;

      case 'CONFIRM_CAST':
        if (step === 'confirm') {
          handleCastBallot();
        } else {
          speak('Primero debe revisar su papeleta diciendo "emitir voto".');
        }
        break;

      case 'HELP':
        speak(
          'Comandos disponibles: "leer papeleta", "elegir opción uno", "voto en blanco", "siguiente cargo", "cargo anterior", "leer resumen", "emitir voto", "confirmar emisión definitiva", "cancelar".'
        );
        break;

      default:
        break;
    }

    setVoiceCommandInput('');
  };

  const handleSelectCandidate = (contestId: string, candidate: CandidateBallotItem, order: number) => {
    setSelections((prev) => ({
      ...prev,
      [contestId]: {
        choiceType: 'CANDIDATE',
        candidateId: candidate.id,
        candidateName: candidate.name,
        candidateNumber: order,
      },
    }));

    if (voiceModeActive) {
      speak(`Seleccionado: ${candidate.name}`);
    }
  };

  const handleSelectBlank = (contestId: string) => {
    setSelections((prev) => ({
      ...prev,
      [contestId]: {
        choiceType: 'BLANK',
        candidateName: 'VOTO EN BLANCO',
      },
    }));

    if (voiceModeActive) {
      speak('Seleccionado Voto en Blanco.');
    }
  };

  const handleSelectNull = (contestId: string) => {
    setSelections((prev) => ({
      ...prev,
      [contestId]: {
        choiceType: 'NULL',
        candidateName: 'VOTO NULO',
      },
    }));

    if (voiceModeActive) {
      speak('Seleccionado Voto Nulo.');
    }
  };

  const handleProceedToConfirm = () => {
    if (!ballot) return;

    // Verificar si todos los cargos tienen selección
    const unselected = ballot.contests.filter((c) => !selections[c.contest_id]);
    if (unselected.length > 0) {
      Alert.alert(
        'Cargos sin marcar',
        `Aún no ha seleccionado una opción para: ${unselected.map((u) => u.contest_name).join(', ')}. ¿Desea continuar y marcarlos en blanco?`,
        [
          { text: 'Volver a marcar', style: 'cancel' },
          {
            text: 'Marcar en blanco y continuar',
            onPress: () => {
              const updated = { ...selections };
              unselected.forEach((u) => {
                updated[u.contest_id] = {
                  choiceType: 'BLANK',
                  candidateName: 'VOTO EN BLANCO',
                };
              });
              setSelections(updated);
              setStep('confirm');
            },
          },
        ]
      );
      return;
    }

    setStep('confirm');
    if (voiceModeActive) {
      speak('Paso de confirmación alcanzado. Revise su selección antes de emitir.');
    }
  };

  const handleCastBallot = async () => {
    if (!ballot) return;

    setCastLoading(true);
    setCastError(null);

    const votesPayload: VoteSelectionItem[] = ballot.contests.map((c) => {
      const sel = selections[c.contest_id] || { choiceType: 'BLANK' };
      return {
        contest_id: c.contest_id,
        constituency_id: c.constituency_id,
        choice_type: sel.choiceType,
        candidate_id: sel.choiceType === 'CANDIDATE' ? sel.candidateId : null,
      };
    });

    try {
      const res = await mobileApi.post<CastReceiptResponse>('/ballot/cast', {
        votes: votesPayload,
      });

      setReceipt(res);
      setStep('receipt');
      setMobileAuthToken(null); // Invalidar token local tras emisión atómica

      if (voiceModeActive) {
        speak(
          `Su voto ha sido emitido y sellado en la urna criptográfica con éxito. Código de comprobante: ${res.verification_code}.`
        );
      }
    } catch (err: any) {
      setCastError(err.message || 'Error al emitir el voto ciego en la urna.');
      if (voiceModeActive) {
        speak(`Error en la emisión del voto: ${err.message || 'Intente nuevamente'}`);
      }
    } finally {
      setCastLoading(false);
    }
  };

  // =========================================================================
  // RENDER: PASO 1 - LOGIN EN CABINA
  // =========================================================================
  if (step === 'login') {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.navRow}>
            <TouchableOpacity onPress={() => onNavigate('home')} style={styles.backButton}>
              <Text style={styles.backButtonText}>← Volver al Portal</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.headerBox}>
            <View style={styles.badgeRow}>
              <View style={styles.boothBadge}>
                <Text style={styles.boothBadgeText}>🗳️ CABINA ELECTORAL SOBERANA</Text>
              </View>
            </View>
            <Text style={styles.title}>Ingreso a la Cabina de Sufragio</Text>
            <Text style={styles.subtitle}>
              Identifíquese con su Cédula y su Credencial de un solo uso emitida para esta elección.
            </Text>
          </View>

          {loginError && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>⚠️ {loginError}</Text>
            </View>
          )}

          <View style={styles.formCard}>
            <Text style={styles.fieldLabel}>Cédula de Identidad (CI)</Text>
            <TextInput
              style={styles.textInput}
              value={documentId}
              onChangeText={setDocumentId}
              placeholder="Ej. 8001002"
              placeholderTextColor="#9CA3AF"
              keyboardType="numeric"
              autoCapitalize="none"
            />

            <Text style={[styles.fieldLabel, { marginTop: 16 }]}>
              Credencial de Votación (Código Secreto VS-...)
            </Text>
            <TextInput
              style={[styles.textInput, styles.codeFont]}
              value={credentialCode}
              onChangeText={setCredentialCode}
              placeholder="Ej. VS-7F3A-89C2"
              placeholderTextColor="#9CA3AF"
              autoCapitalize="characters"
            />
            <Text style={styles.fieldHint}>
              La credencial fue entregada al abrirse la votación o al activar su cuenta.
            </Text>

            <TouchableOpacity
              style={[styles.submitButton, loginLoading && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={loginLoading}
            >
              {loginLoading ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.submitButtonText}>Acceder a la Papeleta Oficial →</Text>
              )}
            </TouchableOpacity>
          </View>

          {/* Invariantes Cívicas */}
          <View style={styles.infoBox}>
            <Text style={styles.infoTitle}>Garantías Criptográficas Inquebrantables:</Text>
            <Text style={styles.infoText}>
              • Su CI y su Credencial generan un Nullifier ciego (HMAC-SHA256).{'\n'}
              • La base de datos jamás vincula su identidad con sus votos (Invariante #9).{'\n'}
              • La credencial queda inutilizada inmediatamente tras emitir su voto.
            </Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // =========================================================================
  // RENDER: PASO 2 - PAPELETA ELECTORAL Y ACCESIBILIDAD POR VOZ (IA-L4)
  // =========================================================================
  if (step === 'ballot' && ballot && currentContest) {
    const isSelected = (candId?: string | null) =>
      selections[currentContest.contest_id]?.choiceType === 'CANDIDATE' &&
      selections[currentContest.contest_id]?.candidateId === candId;

    const isBlank = selections[currentContest.contest_id]?.choiceType === 'BLANK';
    const isNull = selections[currentContest.contest_id]?.choiceType === 'NULL';

    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.navRow}>
            <TouchableOpacity
              onPress={() => {
                Alert.alert('Cerrar Cabina', '¿Desea salir de la cabina de votación?', [
                  { text: 'Cancelar', style: 'cancel' },
                  {
                    text: 'Salir',
                    onPress: () => {
                      setMobileAuthToken(null);
                      setStep('login');
                    },
                  },
                ]);
              }}
              style={styles.backButton}
            >
              <Text style={styles.backButtonText}>✕ Cerrar Sesión</Text>
            </TouchableOpacity>

            {/* Selector de Modo de Voz (IA-L4) */}
            <TouchableOpacity
              style={[
                styles.voiceToggleBtn,
                voiceModeActive ? styles.voiceToggleActive : styles.voiceToggleInactive,
              ]}
              onPress={() => {
                const nextState = !voiceModeActive;
                setVoiceModeActive(nextState);
                if (nextState) {
                  speak(
                    `Modo accesibilidad activado. Cargo actual: ${currentContest.contest_name}. Diga "leer papeleta" para escuchar los candidatos.`
                  );
                } else {
                  setSpokenFeedback(null);
                }
              }}
            >
              <Text style={styles.voiceToggleText}>
                {voiceModeActive ? '🔊 Voz Activada' : '🔇 Activar Voz (IA-L4)'}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Información del Votante y Estamento */}
          <View style={styles.ballotHeaderCard}>
            <Text style={styles.electionTitle}>{ballot.election_name}</Text>
            <Text style={styles.voterEstamento}>
              Elector: {ballot.voter.full_name} • {ballot.voter.group_name}
            </Text>
            <Text style={styles.nodePath}>Mesa / Nodo: {ballot.voter.node_path}</Text>
          </View>

          {/* Barra de Accesibilidad por Voz (IA-L4) */}
          {voiceModeActive && (
            <View style={styles.voiceConsoleCard}>
              <View style={styles.voiceConsoleHeader}>
                <Text style={styles.voiceConsoleTitle}>🎙️ Cabina de Voz Local (IA-L4)</Text>
                <Text style={styles.voiceShieldBadge}>🛡️ 100% On-Device</Text>
              </View>

              {spokenFeedback && (
                <View style={styles.spokenMessageBox}>
                  <Text style={styles.spokenMessageText}>🗣️ "{spokenFeedback}"</Text>
                </View>
              )}

              <Text style={styles.simulatorLabel}>Simulador de Comandos de Voz Rápidos:</Text>
              <View style={styles.voicePillsRow}>
                <TouchableOpacity
                  style={styles.voicePill}
                  onPress={() => handleVoiceCommand('leer papeleta')}
                >
                  <Text style={styles.voicePillText}>📢 Leer candidatos</Text>
                </TouchableOpacity>

                {currentContest.candidates.map((_, i) => (
                  <TouchableOpacity
                    key={i}
                    style={styles.voicePill}
                    onPress={() => handleVoiceCommand(`elegir opcion ${i + 1}`)}
                  >
                    <Text style={styles.voicePillText}>👉 Opción {i + 1}</Text>
                  </TouchableOpacity>
                ))}

                <TouchableOpacity
                  style={styles.voicePill}
                  onPress={() => handleVoiceCommand('voto en blanco')}
                >
                  <Text style={styles.voicePillText}>⬜ Voto en blanco</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.voicePill}
                  onPress={() => handleVoiceCommand('siguiente cargo')}
                >
                  <Text style={styles.voicePillText}>⏭️ Siguiente</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.voicePill, { backgroundColor: '#ECFDF5' }]}
                  onPress={() => handleVoiceCommand('emitir voto')}
                >
                  <Text style={[styles.voicePillText, { color: '#047857' }]}>🗳️ Emitir voto</Text>
                </TouchableOpacity>
              </View>

              {/* Entrada de texto simulada para comandos libres */}
              <View style={styles.voiceInputRow}>
                <TextInput
                  style={styles.voiceTextInput}
                  value={voiceCommandInput}
                  onChangeText={setVoiceCommandInput}
                  placeholder="Dictar comando por texto (ej. votar por opción 1)..."
                  placeholderTextColor="#9CA3AF"
                  onSubmitEditing={() => handleVoiceCommand(voiceCommandInput)}
                />
                <TouchableOpacity
                  style={styles.voiceSendBtn}
                  onPress={() => handleVoiceCommand(voiceCommandInput)}
                >
                  <Text style={styles.voiceSendText}>Dictar</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* Navegador de Cargos */}
          <View style={styles.contestTabsContainer}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {ballot.contests.map((c, idx) => {
                const isCurrent = idx === currentContestIdx;
                const isMarked = !!selections[c.contest_id];
                return (
                  <TouchableOpacity
                    key={c.contest_id}
                    style={[
                      styles.contestTab,
                      isCurrent && styles.contestTabCurrent,
                      isMarked && !isCurrent && styles.contestTabMarked,
                    ]}
                    onPress={() => {
                      setCurrentContestIdx(idx);
                      if (voiceModeActive) {
                        speak(`Cambiando a ${c.contest_name}.`);
                      }
                    }}
                  >
                    <Text
                      style={[
                        styles.contestTabText,
                        isCurrent && styles.contestTabTextCurrent,
                        isMarked && !isCurrent && styles.contestTabTextMarked,
                      ]}
                    >
                      {isMarked ? '✓ ' : ''}
                      {c.contest_name}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>

          {/* Tarjeta del Cargo Actual */}
          <View style={styles.contestCard}>
            <View style={styles.contestCardHeader}>
              <Text style={styles.contestName}>{currentContest.contest_name}</Text>
              <Text style={styles.contestScope}>
                Alcance: {currentContest.scope_level_name} ({currentContest.node_name})
              </Text>
              {currentContest.description && (
                <Text style={styles.contestDesc}>{currentContest.description}</Text>
              )}
            </View>

            {/* Lista de Candidatos */}
            <View style={styles.candidatesList}>
              {currentContest.candidates.map((cand, idx) => {
                const selected = isSelected(cand.id);
                return (
                  <TouchableOpacity
                    key={cand.id}
                    style={[styles.candidateRow, selected && styles.candidateRowSelected]}
                    onPress={() => handleSelectCandidate(currentContest.contest_id, cand, idx + 1)}
                    activeOpacity={0.8}
                  >
                    <View
                      style={[
                        styles.candidateNumberBox,
                        selected && styles.candidateNumberBoxSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.candidateNumberText,
                          selected && styles.candidateNumberTextSelected,
                        ]}
                      >
                        {idx + 1}
                      </Text>
                    </View>

                    <View style={styles.candidateInfo}>
                      <Text style={[styles.candidateName, selected && styles.candidateNameSelected]}>
                        {cand.name}
                      </Text>
                      <Text style={styles.candidateParty}>
                        {cand.party_or_front || 'Candidatura Independiente'}
                      </Text>
                    </View>

                    <View style={[styles.radioCircle, selected && styles.radioCircleSelected]}>
                      {selected && <View style={styles.radioInnerCircle} />}
                    </View>
                  </TouchableOpacity>
                );
              })}

              {/* Voto en Blanco */}
              {currentContest.allow_blank && (
                <TouchableOpacity
                  style={[styles.candidateRow, isBlank && styles.candidateRowSelected]}
                  onPress={() => handleSelectBlank(currentContest.contest_id)}
                  activeOpacity={0.8}
                >
                  <View style={[styles.candidateNumberBox, isBlank && styles.candidateNumberBoxSelected]}>
                    <Text style={[styles.candidateNumberText, isBlank && styles.candidateNumberTextSelected]}>
                      ⬜
                    </Text>
                  </View>
                  <View style={styles.candidateInfo}>
                    <Text style={[styles.candidateName, isBlank && styles.candidateNameSelected]}>
                      VOTO EN BLANCO
                    </Text>
                    <Text style={styles.candidateParty}>
                      No respaldar ninguna de las candidaturas registradas
                    </Text>
                  </View>
                  <View style={[styles.radioCircle, isBlank && styles.radioCircleSelected]}>
                    {isBlank && <View style={styles.radioInnerCircle} />}
                  </View>
                </TouchableOpacity>
              )}

              {/* Voto Nulo */}
              {currentContest.allow_null && (
                <TouchableOpacity
                  style={[styles.candidateRow, isNull && styles.candidateRowSelected]}
                  onPress={() => handleSelectNull(currentContest.contest_id)}
                  activeOpacity={0.8}
                >
                  <View style={[styles.candidateNumberBox, isNull && styles.candidateNumberBoxSelected]}>
                    <Text style={[styles.candidateNumberText, isNull && styles.candidateNumberTextSelected]}>
                      ✖️
                    </Text>
                  </View>
                  <View style={styles.candidateInfo}>
                    <Text style={[styles.candidateName, isNull && styles.candidateNameSelected]}>
                      VOTO NULO
                    </Text>
                    <Text style={styles.candidateParty}>Anular voluntariamente este cargo</Text>
                  </View>
                  <View style={[styles.radioCircle, isNull && styles.radioCircleSelected]}>
                    {isNull && <View style={styles.radioInnerCircle} />}
                  </View>
                </TouchableOpacity>
              )}
            </View>
          </View>

          {/* Navegación y Botón de Emisión */}
          <View style={styles.actionFooterRow}>
            {currentContestIdx > 0 && (
              <TouchableOpacity
                style={styles.navArrowBtn}
                onPress={() => setCurrentContestIdx((prev) => prev - 1)}
              >
                <Text style={styles.navArrowText}>← Anterior</Text>
              </TouchableOpacity>
            )}

            {currentContestIdx < ballot.contests.length - 1 ? (
              <TouchableOpacity
                style={[styles.navArrowBtn, styles.navArrowNext]}
                onPress={() => setCurrentContestIdx((prev) => prev + 1)}
              >
                <Text style={[styles.navArrowText, { color: '#FFFFFF' }]}>Siguiente Cargo →</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                style={[styles.navArrowBtn, styles.navArrowCast]}
                onPress={handleProceedToConfirm}
              >
                <Text style={[styles.navArrowText, { color: '#FFFFFF' }]}>
                  Revisar y Emitir Voto →
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // =========================================================================
  // RENDER: PASO 3 - REVISIÓN Y CONFIRMACIÓN IRREVERSIBLE
  // =========================================================================
  if (step === 'confirm' && ballot) {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.navRow}>
            <TouchableOpacity onPress={() => setStep('ballot')} style={styles.backButton}>
              <Text style={styles.backButtonText}>← Volver a Modificar Opciones</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.headerBox}>
            <View style={styles.badgeRow}>
              <View style={[styles.boothBadge, { backgroundColor: 'rgba(239, 68, 68, 0.1)' }]}>
                <Text style={[styles.boothBadgeText, { color: '#DC2626' }]}>
                  ⚠️ REVISIÓN FINAL IRREVERSIBLE
                </Text>
              </View>
            </View>
            <Text style={styles.title}>Confirmación de Sufragio Ciego</Text>
            <Text style={styles.subtitle}>
              Revise cuidadosamente cada cargo. Una vez depositada en la urna, la papeleta no puede
              modificarse ni anularse.
            </Text>
          </View>

          {castError && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>⚠️ {castError}</Text>
            </View>
          )}

          {/* Resumen de Selecciones */}
          <View style={styles.summaryCard}>
            {ballot.contests.map((c) => {
              const sel = selections[c.contest_id];
              return (
                <View key={c.contest_id} style={styles.summaryRow}>
                  <Text style={styles.summaryContestName}>{c.contest_name}</Text>
                  <Text style={styles.summaryChoiceName}>
                    {sel ? sel.candidateName : 'VOTO EN BLANCO'}
                  </Text>
                </View>
              );
            })}
          </View>

          {/* Consola de Voz en Confirmación */}
          {voiceModeActive && (
            <View style={styles.voiceConsoleCard}>
              <Text style={styles.voiceConsoleTitle}>🎙️ Confirmación por Voz (IA-L4)</Text>
              <Text style={styles.fieldHint}>
                Diga en voz alta: "confirmar emisión definitiva" o presione el botón de abajo.
              </Text>
              <TouchableOpacity
                style={[styles.voicePill, { marginTop: 10, backgroundColor: '#DC2626' }]}
                onPress={() => handleVoiceCommand('confirmar emision definitiva')}
              >
                <Text style={[styles.voicePillText, { color: '#FFFFFF' }]}>
                  🗣️ Simular: "Confirmar emisión definitiva"
                </Text>
              </TouchableOpacity>
            </View>
          )}

          <TouchableOpacity
            style={[styles.castFinalButton, castLoading && styles.buttonDisabled]}
            onPress={handleCastBallot}
            disabled={castLoading}
          >
            {castLoading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.castFinalButtonText}>
                🔒 Confirmar y Depositar Papeleta en Urna
              </Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // =========================================================================
  // RENDER: PASO 4 - COMPROBANTE CRIPTOGRÁFICO OFICIAL
  // =========================================================================
  if (step === 'receipt' && receipt) {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.successHeaderCard}>
            <Text style={styles.successIcon}>🎉</Text>
            <Text style={styles.successTitle}>¡Sufragio Depositado con Éxito!</Text>
            <Text style={styles.successSubtitle}>
              Su voto ha sido sellado de forma ciega e irreversible en la urna criptográfica.
            </Text>
          </View>

          <View style={styles.receiptCard}>
            <View style={styles.receiptHeader}>
              <Text style={styles.receiptCardTitle}>COMPROBANTE ELECTORAL OFICIAL</Text>
              <Text style={styles.receiptElectionName}>{receipt.election_name}</Text>
            </View>

            <View style={styles.receiptFieldGroup}>
              <Text style={styles.receiptFieldLabel}>Código de Verificación:</Text>
              <Text style={styles.receiptCodeValue}>{receipt.verification_code}</Text>
            </View>

            <View style={styles.receiptFieldGroup}>
              <Text style={styles.receiptFieldLabel}>Huella Criptográfica (Receipt Hash):</Text>
              <Text style={styles.receiptHashValue}>{receipt.receipt_hash}</Text>
            </View>

            <View style={styles.receiptFieldGroup}>
              <Text style={styles.receiptFieldLabel}>Fecha y Hora de Emisión:</Text>
              <Text style={styles.receiptDateValue}>
                {new Date(receipt.cast_at).toLocaleString('es-BO')}
              </Text>
            </View>

            <View style={styles.receiptFieldGroup}>
              <Text style={styles.receiptFieldLabel}>Cargos Sufragados:</Text>
              <Text style={styles.receiptDateValue}>{receipt.votes_count} cargos registrados</Text>
            </View>

            <View style={styles.receiptNotice}>
              <Text style={styles.receiptNoticeText}>
                🔐 Este comprobante prueba matemáticamente que su papeleta está incluida en la urna
                sin revelar en ningún momento el sentido de sus votos (Invariante #9).
              </Text>
            </View>
          </View>

          {/* Botones de acción */}
          <TouchableOpacity
            style={styles.verifyNavButton}
            onPress={() =>
              onNavigate('receipt', {
                receiptHash: receipt.receipt_hash,
                electionId: ballot?.election_id,
              })
            }
          >
            <Text style={styles.verifyNavButtonText}>
              🔍 Auditar Comprobante en la Cadena de Votos (S2-03) →
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.exitButton}
            onPress={() => {
              setBallot(null);
              setReceipt(null);
              setSelections({});
              setStep('login');
              onNavigate('home');
            }}
          >
            <Text style={styles.exitButtonText}>Finalizar y Salir</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ActivityIndicator size="large" color="#047857" style={{ marginTop: 60 }} />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F7F4',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  navRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  backButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  backButtonText: {
    color: '#4B5563',
    fontWeight: '700',
    fontSize: 14,
  },
  voiceToggleBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
  },
  voiceToggleActive: {
    backgroundColor: '#ECFDF5',
    borderColor: '#047857',
  },
  voiceToggleInactive: {
    backgroundColor: '#F3F4F6',
    borderColor: '#D1D5DB',
  },
  voiceToggleText: {
    fontSize: 12,
    fontWeight: '800',
    color: '#047857',
  },
  headerBox: {
    marginBottom: 20,
  },
  badgeRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  boothBadge: {
    backgroundColor: 'rgba(4, 120, 87, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#047857',
  },
  boothBadgeText: {
    color: '#047857',
    fontSize: 11,
    fontWeight: '800',
  },
  title: {
    fontSize: 24,
    fontWeight: '900',
    color: '#111827',
  },
  subtitle: {
    fontSize: 13,
    color: '#4B5563',
    marginTop: 4,
    lineHeight: 18,
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 6,
  },
  fieldHint: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 4,
  },
  textInput: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 15,
    color: '#111827',
  },
  codeFont: {
    fontFamily: 'monospace',
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  submitButton: {
    backgroundColor: '#047857',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 20,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  errorBox: {
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#F87171',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: '#B91C1C',
    fontSize: 13,
    fontWeight: '600',
  },
  infoBox: {
    backgroundColor: '#F0FDF4',
    borderWidth: 1,
    borderColor: '#BBF7D0',
    borderRadius: 12,
    padding: 14,
  },
  infoTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: '#166534',
    marginBottom: 4,
  },
  infoText: {
    fontSize: 11,
    color: '#15803D',
    lineHeight: 18,
  },
  ballotHeaderCard: {
    backgroundColor: '#0B132B',
    borderRadius: 16,
    padding: 18,
    marginBottom: 16,
  },
  electionTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  voterEstamento: {
    fontSize: 12,
    color: '#D1D5DB',
    marginTop: 4,
    fontWeight: '600',
  },
  nodePath: {
    fontSize: 11,
    color: '#34D399',
    marginTop: 2,
    fontFamily: 'monospace',
  },
  voiceConsoleCard: {
    backgroundColor: '#F0F9FF',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1.5,
    borderColor: '#0284C7',
    marginBottom: 16,
  },
  voiceConsoleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  voiceConsoleTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#0369A1',
  },
  voiceShieldBadge: {
    fontSize: 10,
    fontWeight: '800',
    color: '#0284C7',
    backgroundColor: '#E0F2FE',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  spokenMessageBox: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    padding: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#BAE6FD',
  },
  spokenMessageText: {
    fontSize: 12,
    color: '#0C4A6E',
    fontStyle: 'italic',
    fontWeight: '600',
  },
  simulatorLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#0369A1',
    marginBottom: 6,
  },
  voicePillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 10,
  },
  voicePill: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#7DD3FC',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  voicePillText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#0284C7',
  },
  voiceInputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  voiceTextInput: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#BAE6FD',
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 12,
    color: '#0C4A6E',
  },
  voiceSendBtn: {
    backgroundColor: '#0284C7',
    borderRadius: 8,
    paddingHorizontal: 14,
    justifyContent: 'center',
  },
  voiceSendText: {
    color: '#FFFFFF',
    fontWeight: '800',
    fontSize: 12,
  },
  contestTabsContainer: {
    marginBottom: 14,
  },
  contestTab: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#E5E7EB',
    marginRight: 8,
  },
  contestTabCurrent: {
    backgroundColor: '#047857',
  },
  contestTabMarked: {
    backgroundColor: '#D1FAE5',
    borderWidth: 1,
    borderColor: '#059669',
  },
  contestTabText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4B5563',
  },
  contestTabTextCurrent: {
    color: '#FFFFFF',
  },
  contestTabTextMarked: {
    color: '#065F46',
  },
  contestCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 16,
  },
  contestCardHeader: {
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    paddingBottom: 12,
    marginBottom: 14,
  },
  contestName: {
    fontSize: 17,
    fontWeight: '800',
    color: '#111827',
  },
  contestScope: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  contestDesc: {
    fontSize: 12,
    color: '#4B5563',
    marginTop: 4,
    fontStyle: 'italic',
  },
  candidatesList: {
    gap: 10,
  },
  candidateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#E5E7EB',
    backgroundColor: '#F9FAFB',
  },
  candidateRowSelected: {
    borderColor: '#047857',
    backgroundColor: '#ECFDF5',
  },
  candidateNumberBox: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#E5E7EB',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  candidateNumberBoxSelected: {
    backgroundColor: '#047857',
  },
  candidateNumberText: {
    fontSize: 13,
    fontWeight: '800',
    color: '#374151',
  },
  candidateNumberTextSelected: {
    color: '#FFFFFF',
  },
  candidateInfo: {
    flex: 1,
  },
  candidateName: {
    fontSize: 14,
    fontWeight: '800',
    color: '#1F2937',
  },
  candidateNameSelected: {
    color: '#065F46',
  },
  candidateParty: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 1,
  },
  radioCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#9CA3AF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioCircleSelected: {
    borderColor: '#047857',
  },
  radioInnerCircle: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#047857',
  },
  actionFooterRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 10,
  },
  navArrowBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: '#E5E7EB',
    alignItems: 'center',
  },
  navArrowNext: {
    backgroundColor: '#1E293B',
  },
  navArrowCast: {
    backgroundColor: '#047857',
  },
  navArrowText: {
    fontSize: 14,
    fontWeight: '800',
    color: '#374151',
  },
  summaryCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 20,
    gap: 12,
  },
  summaryRow: {
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    paddingBottom: 10,
  },
  summaryContestName: {
    fontSize: 12,
    fontWeight: '700',
    color: '#6B7280',
    textTransform: 'uppercase',
  },
  summaryChoiceName: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
    marginTop: 2,
  },
  castFinalButton: {
    backgroundColor: '#047857',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#047857',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  castFinalButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
  successHeaderCard: {
    backgroundColor: '#ECFDF5',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#6EE7B7',
  },
  successIcon: {
    fontSize: 48,
    marginBottom: 10,
  },
  successTitle: {
    fontSize: 22,
    fontWeight: '900',
    color: '#065F46',
    textAlign: 'center',
  },
  successSubtitle: {
    fontSize: 13,
    color: '#047857',
    textAlign: 'center',
    marginTop: 6,
  },
  receiptCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 20,
    gap: 14,
  },
  receiptHeader: {
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
    paddingBottom: 12,
  },
  receiptCardTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#6B7280',
    letterSpacing: 1,
  },
  receiptElectionName: {
    fontSize: 16,
    fontWeight: '900',
    color: '#111827',
    marginTop: 2,
  },
  receiptFieldGroup: {},
  receiptFieldLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4B5563',
  },
  receiptCodeValue: {
    fontSize: 20,
    fontWeight: '900',
    color: '#047857',
    fontFamily: 'monospace',
    letterSpacing: 1,
    marginTop: 2,
  },
  receiptHashValue: {
    fontSize: 11,
    color: '#1F2937',
    fontFamily: 'monospace',
    backgroundColor: '#F3F4F6',
    padding: 8,
    borderRadius: 8,
    marginTop: 4,
  },
  receiptDateValue: {
    fontSize: 13,
    color: '#111827',
    fontWeight: '600',
    marginTop: 2,
  },
  receiptNotice: {
    backgroundColor: '#F0FDF4',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#BBF7D0',
    marginTop: 6,
  },
  receiptNoticeText: {
    fontSize: 11,
    color: '#166534',
    lineHeight: 16,
  },
  verifyNavButton: {
    backgroundColor: '#0B132B',
    borderRadius: 14,
    paddingVertical: 15,
    alignItems: 'center',
    marginBottom: 12,
  },
  verifyNavButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  exitButton: {
    backgroundColor: '#E5E7EB',
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
  },
  exitButtonText: {
    color: '#374151',
    fontSize: 14,
    fontWeight: '800',
  },
});
