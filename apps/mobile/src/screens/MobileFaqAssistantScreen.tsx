import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native';
import { mobileApi } from '../api/mobile-client';
import { AssistantQuestionRequest, AssistantAnswerResponse, DocumentCitation } from '@votoseguro/api-client';

interface MobileFaqAssistantScreenProps {
  onNavigate: (screen: 'home' | 'register' | 'booth' | 'receipt' | 'faq', params?: any) => void;
}

const FAQ_SUGGESTIONS = [
  '¿Cómo activo mi cuenta de votante?',
  '¿Dónde encuentro mi comprobante de voto?',
  '¿Qué garantías de privacidad y secreto existen?',
  '¿Quién ganará la elección?',
  '¿Qué pasa si pierdo mi credencial?',
];

export const MobileFaqAssistantScreen: React.FC<MobileFaqAssistantScreenProps> = ({ onNavigate }) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AssistantAnswerResponse[]>([]);

  const handleAsk = async (queryText: string) => {
    const textToAsk = queryText.trim() || question.trim();
    if (!textToAsk) return;

    setLoading(true);
    setError(null);

    try {
      const payload: AssistantQuestionRequest = {
        question: textToAsk,
      };

      const res = await mobileApi.post<AssistantAnswerResponse>('/ai/assistant/ask', payload);
      setHistory((prev) => [res, ...prev]);
      setQuestion('');
    } catch (err: any) {
      setError(err.message || 'No se pudo obtener respuesta del asistente electoral.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Navegación Superior */}
        <View style={styles.navRow}>
          <TouchableOpacity onPress={() => onNavigate('home')} style={styles.backButton}>
            <Text style={styles.backButtonText}>← Volver al Portal</Text>
          </TouchableOpacity>
        </View>

        {/* Encabezado */}
        <View style={styles.headerBox}>
          <View style={styles.badgeRow}>
            <View style={styles.aiBadge}>
              <Text style={styles.aiBadgeText}>🤖 ASISTENTE ELECTORAL RAG (IA-L5)</Text>
            </View>
          </View>
          <Text style={styles.title}>Guía Electoral Oficial</Text>
          <Text style={styles.subtitle}>
            Respuestas operativas basadas exclusivamente en los 12 manuales normativos de VotoSeguro
            con citas textuales verificables.
          </Text>
        </View>

        {/* Sugerencias Rápidas */}
        <View style={styles.suggestionsContainer}>
          <Text style={styles.suggestionsTitle}>Preguntas frecuentes sugeridas:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {FAQ_SUGGESTIONS.map((sug, i) => (
              <TouchableOpacity
                key={i}
                style={styles.suggestionPill}
                onPress={() => {
                  setQuestion(sug);
                  handleAsk(sug);
                }}
              >
                <Text style={styles.suggestionPillText}>{sug}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Formulario de Pregunta */}
        <View style={styles.askCard}>
          <TextInput
            style={styles.textInput}
            value={question}
            onChangeText={setQuestion}
            placeholder="Escriba su consulta operativa electoral..."
            placeholderTextColor="#9CA3AF"
            multiline
            numberOfLines={3}
          />

          <TouchableOpacity
            style={[styles.askButton, loading && styles.buttonDisabled]}
            onPress={() => handleAsk(question)}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.askButtonText}>Consultar al Asistente →</Text>
            )}
          </TouchableOpacity>
        </View>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {/* Historial de Respuestas */}
        <View style={styles.historyContainer}>
          {history.map((item, idx) => (
            <View key={idx} style={styles.answerCard}>
              <View style={styles.questionBubble}>
                <Text style={styles.questionLabel}>Pregunta del elector:</Text>
                <Text style={styles.questionText}>"{item.question}"</Text>
              </View>

              <View style={styles.answerHeader}>
                <Text style={styles.answerHeaderTitle}>Dictamen Normativo Oficial:</Text>
                <View
                  style={[
                    styles.sourceTag,
                    item.source === 'LFM3-1.7B' ? styles.sourceTagLlm : styles.sourceTagFallback,
                  ]}
                >
                  <Text style={styles.sourceTagText}>
                    {item.source === 'LFM3-1.7B' ? '🤖 LFM3-1.7B Local' : '⚡ Modo Degradado'}
                  </Text>
                </View>
              </View>

              <Text style={styles.answerBodyText}>{item.answer}</Text>

              {/* Documentos de Respaldo RAG */}
              {((item.citations && item.citations.length > 0) || (item.sources && item.sources.length > 0)) && (
                <View style={styles.sourcesBox}>
                  <Text style={styles.sourcesTitle}>Fundamentos Documentales Oficiales:</Text>
                  {(item.citations || item.sources || []).map((src: DocumentCitation, sIdx: number) => (
                    <View key={sIdx} style={styles.sourceItem}>
                      <Text style={styles.sourceDocId}>[{src.doc_id}]</Text>
                      <View style={styles.sourceContent}>
                        <Text style={styles.sourceDocTitle}>
                          {src.title} {src.section ? `— ${src.section}` : ''}
                        </Text>
                        <Text style={styles.sourceExcerpt}>"{src.excerpt}"</Text>
                      </View>
                    </View>
                  ))}
                </View>
              )}

              {/* Derivación a Soporte */}
              {item.suggests_support && (
                <View style={styles.supportBox}>
                  <Text style={styles.supportText}>
                    ℹ️ Esta consulta requiere atención presencial. Acérquese a su mesa de sufragio o
                    contacte al Administrador Electoral de su unidad.
                  </Text>
                </View>
              )}

              <Text style={styles.latencyMeta}>Respuesta generada en {item.latency_ms} ms</Text>
            </View>
          ))}
        </View>
      </ScrollView>
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
  headerBox: {
    marginBottom: 16,
  },
  badgeRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  aiBadge: {
    backgroundColor: 'rgba(217, 119, 6, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#D97706',
  },
  aiBadgeText: {
    color: '#B45309',
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
  suggestionsContainer: {
    marginBottom: 16,
  },
  suggestionsTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 8,
  },
  suggestionPill: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
  },
  suggestionPillText: {
    fontSize: 12,
    color: '#374151',
    fontWeight: '600',
  },
  askCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  textInput: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: '#111827',
    textAlignVertical: 'top',
    minHeight: 70,
  },
  askButton: {
    backgroundColor: '#B45309',
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 12,
  },
  askButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
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
  historyContainer: {
    gap: 16,
  },
  answerCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  questionBubble: {
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
  },
  questionLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#6B7280',
    textTransform: 'uppercase',
  },
  questionText: {
    fontSize: 13,
    fontWeight: '800',
    color: '#111827',
    marginTop: 2,
  },
  answerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  answerHeaderTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#111827',
  },
  sourceTag: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  sourceTagLlm: {
    backgroundColor: '#EFF6FF',
    borderWidth: 1,
    borderColor: '#3B82F6',
  },
  sourceTagFallback: {
    backgroundColor: '#FEF3C7',
    borderWidth: 1,
    borderColor: '#F59E0B',
  },
  sourceTagText: {
    fontSize: 10,
    fontWeight: '800',
    color: '#1F2937',
  },
  answerBodyText: {
    fontSize: 14,
    color: '#1F2937',
    lineHeight: 22,
    marginBottom: 12,
  },
  sourcesBox: {
    backgroundColor: '#F9FAFB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 10,
  },
  sourcesTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#4B5563',
    marginBottom: 6,
  },
  sourceItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  sourceDocId: {
    fontSize: 10,
    fontWeight: '800',
    color: '#B45309',
    fontFamily: 'monospace',
    marginRight: 6,
    marginTop: 2,
  },
  sourceContent: {
    flex: 1,
  },
  sourceDocTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#374151',
  },
  sourceExcerpt: {
    fontSize: 11,
    color: '#6B7280',
    fontStyle: 'italic',
    marginTop: 1,
  },
  supportBox: {
    backgroundColor: '#FEF3C7',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#FDE68A',
    marginBottom: 8,
  },
  supportText: {
    fontSize: 11,
    color: '#92400E',
    fontWeight: '600',
    lineHeight: 16,
  },
  latencyMeta: {
    fontSize: 10,
    color: '#9CA3AF',
    fontFamily: 'monospace',
    textAlign: 'right',
  },
});
