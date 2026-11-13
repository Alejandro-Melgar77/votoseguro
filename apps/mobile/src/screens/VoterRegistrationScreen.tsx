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
  Alert,
} from 'react-native';
import { mobileApi } from '../api/mobile-client';
import { IdCardExtractionResponse, PublicActivationResponse } from '@votoseguro/api-client';

interface VoterRegistrationScreenProps {
  initialToken?: string;
  onNavigate: (screen: 'home' | 'register' | 'booth' | 'receipt' | 'faq', params?: any) => void;
}

const OCR_DEMO_SAMPLES = [
  {
    name: 'Cédula Demo 1 (Juan Carlos Pérez - 8001002)',
    text: 'ESTADO PLURINACIONAL DE BOLIVIA CEDULA DE IDENTIDAD N° 8001002 SC NOMBRES: JUAN CARLOS APELLIDOS: PEREZ GOMEZ FECHA DE NACIMIENTO: 14/05/2001',
  },
  {
    name: 'Cédula Demo 2 (María Elena Rojas - 8001003)',
    text: 'ESTADO PLURINACIONAL DE BOLIVIA CEDULA DE IDENTIDAD N° 8001003 SC NOMBRES: MARIA ELENA APELLIDOS: ROJAS SUAREZ FECHA DE NACIMIENTO: 22/09/2002',
  },
  {
    name: 'Cédula Demo 3 (Roberto Callau - 8001008)',
    text: 'ESTADO PLURINACIONAL DE BOLIVIA CEDULA DE IDENTIDAD N° 8001008 SC NOMBRES: ROBERTO APELLIDOS: CALLAU MELGAR FECHA DE NACIMIENTO: 10/11/1985',
  },
];

export const VoterRegistrationScreen: React.FC<VoterRegistrationScreenProps> = ({
  initialToken = '',
  onNavigate,
}) => {
  const [token, setToken] = useState(initialToken);
  const [documentId, setDocumentId] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estado OCR
  const [showOcrSheet, setShowOcrSheet] = useState(false);
  const [ocrText, setOcrText] = useState(OCR_DEMO_SAMPLES[0].text);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [extractedOcr, setExtractedOcr] = useState<IdCardExtractionResponse | null>(null);

  // Resultado de Activación
  const [activationResult, setActivationResult] = useState<PublicActivationResponse | null>(null);

  const handleScanOcr = async () => {
    setOcrLoading(true);
    try {
      const res = await mobileApi.post<IdCardExtractionResponse>('/ai/id-card/extract', {
        raw_ocr_text: ocrText,
      });
      setExtractedOcr(res);
      setDocumentId(res.ci);
    } catch (err: any) {
      Alert.alert('Error OCR', err.message || 'Error al analizar el texto OCR de la cédula.');
    } finally {
      setOcrLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!token.trim()) {
      setError('Ingrese el token o código del enlace de invitación.');
      return;
    }
    if (!documentId.trim()) {
      setError('Ingrese su número de Cédula de Identidad.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const cleanToken = token.trim().replace(/^.*\/register\//, '');
      const res = await mobileApi.post<PublicActivationResponse>(`/register/${cleanToken}`, {
        document_id: documentId.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
      });
      setActivationResult(res);
    } catch (err: any) {
      setError(err.message || 'Error al activar el registro de elector.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Cabecera */}
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => onNavigate('home')} style={styles.backBtn}>
            <Text style={styles.backBtnText}>← Volver al Portal</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.titleCard}>
          <Text style={styles.screenEmoji}>🪪</Text>
          <Text style={styles.screenTitle}>Activación de Elector Móvil</Text>
          <Text style={styles.screenSubtitle}>
            Enlace de registro (S1-08) y extracción OCR con IA Local (IA-L3)
          </Text>
        </View>

        {/* Modal / Sección OCR en Dispositivo */}
        <View style={styles.ocrBox}>
          <View style={styles.ocrHeaderRow}>
            <Text style={styles.ocrTitle}>Escáner OCR de Cédula de Identidad (IA-L3)</Text>
            <TouchableOpacity
              onPress={() => setShowOcrSheet(!showOcrSheet)}
              style={styles.ocrToggleBtn}
            >
              <Text style={styles.ocrToggleText}>
                {showOcrSheet ? 'Ocultar' : '📷 Abrir Escáner OCR'}
              </Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.privacyNote}>
            🔒 Invariante #15: La imagen se procesa localmente en su dispositivo y nunca se envía al servidor.
          </Text>

          {showOcrSheet && (
            <View style={styles.ocrContent}>
              <Text style={styles.ocrHelper}>Seleccione una plantilla demo de cédula o edite el texto:</Text>
              <View style={styles.templateButtonsRow}>
                {OCR_DEMO_SAMPLES.map((s, idx) => (
                  <TouchableOpacity
                    key={idx}
                    onPress={() => {
                      setOcrText(s.text);
                      setExtractedOcr(null);
                    }}
                    style={[
                      styles.templateChip,
                      ocrText === s.text && styles.templateChipActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.templateChipText,
                        ocrText === s.text && styles.templateChipTextActive,
                      ]}
                    >
                      Demo {idx + 1}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <TextInput
                multiline
                numberOfLines={3}
                value={ocrText}
                onChangeText={setOcrText}
                style={styles.ocrInput}
              />

              <TouchableOpacity
                onPress={handleScanOcr}
                disabled={ocrLoading}
                style={styles.ocrScanBtn}
              >
                {ocrLoading ? (
                  <ActivityIndicator color="#FFFFFF" size="small" />
                ) : (
                  <Text style={styles.ocrScanBtnText}>✨ Analizar con LFM3-1.7B</Text>
                )}
              </TouchableOpacity>

              {extractedOcr && (
                <View style={styles.ocrResultCard}>
                  <Text style={styles.ocrResultTitle}>✅ Cédula detectada y validada por regex:</Text>
                  <Text style={styles.ocrResultField}>CI: <Text style={styles.bold}>{extractedOcr.ci}</Text></Text>
                  <Text style={styles.ocrResultField}>Nombres: <Text style={styles.bold}>{extractedOcr.nombres}</Text></Text>
                  <Text style={styles.ocrResultField}>Apellidos: <Text style={styles.bold}>{extractedOcr.apellidos}</Text></Text>
                  <Text style={styles.ocrResultField}>Nacimiento: <Text style={styles.bold}>{extractedOcr.fecha_nacimiento || 'N/A'}</Text></Text>
                  <Text style={styles.ocrResultSource}>
                    {extractedOcr.ai_source?.includes('NEURAL_TUNNEL')
                      ? `🧠 Inferencia PC Local vía Túnel Estático (${extractedOcr.model_name || 'votoseguro-lfm3'})`
                      : extractedOcr.ai_source === 'LFM3-1.7B'
                      ? '🤖 LFM3-1.7B Local'
                      : '⚙️ Modo Degradado Determinista'}
                  </Text>
                </View>
              )}
            </View>
          )}
        </View>

        {/* Formulario de Activación */}
        {!activationResult ? (
          <View style={styles.formCard}>
            {error && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>⚠️ {error}</Text>
              </View>
            )}

            <Text style={styles.fieldLabel}>Token o Enlace de Invitación *</Text>
            <TextInput
              value={token}
              onChangeText={setToken}
              placeholder="Ej. votoseguro://register/TOKEN o código alfanumérico"
              style={styles.input}
              autoCapitalize="none"
            />

            <Text style={styles.fieldLabel}>Cédula de Identidad (CI / DNI) *</Text>
            <TextInput
              value={documentId}
              onChangeText={setDocumentId}
              placeholder="Ej. CI-8001002"
              style={[styles.input, styles.monoInput]}
              autoCapitalize="characters"
            />

            <Text style={styles.fieldLabel}>Correo Electrónico (Opcional)</Text>
            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder="su-correo@institucion.edu"
              style={styles.input}
              keyboardType="email-address"
              autoCapitalize="none"
            />

            <Text style={styles.fieldLabel}>Teléfono de Contacto (Opcional)</Text>
            <TextInput
              value={phone}
              onChangeText={setPhone}
              placeholder="+591 7XXXXXXX"
              style={styles.input}
              keyboardType="phone-pad"
            />

            <TouchableOpacity
              onPress={handleActivate}
              disabled={loading}
              style={styles.submitBtn}
            >
              {loading ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.submitBtnText}>✓ Activar mi Registro Oficial</Text>
              )}
            </TouchableOpacity>
          </View>
        ) : (
          /* Certificado de Activación */
          <View style={styles.successCard}>
            <Text style={styles.successEmoji}>🎉</Text>
            <Text style={styles.successTitle}>¡Registro Activado Exitosamente!</Text>
            <Text style={styles.successSubtitle}>{activationResult.message}</Text>

            <View style={styles.credentialBox}>
              <Text style={styles.credentialLabel}>CREDENCIAL PERSONAL DE VOTACIÓN:</Text>
              <Text style={styles.credentialCode}>
                {activationResult.credential_code || 'VS-DEMO-2026-OK'}
              </Text>
              <Text style={styles.credentialWarning}>
                ⚠️ Guarde este código confidencial. Es de un solo uso y se destruye al emitir su voto.
              </Text>
            </View>

            <TouchableOpacity
              onPress={() =>
                onNavigate('booth', {
                  documentId: activationResult.document_id,
                  credentialCode: activationResult.credential_code,
                })
              }
              style={styles.goToBoothBtn}
            >
              <Text style={styles.goToBoothBtnText}>🗳️ Ir a la Cabina de Votación →</Text>
            </TouchableOpacity>
          </View>
        )}
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
  topBar: {
    marginBottom: 12,
  },
  backBtn: {
    paddingVertical: 6,
  },
  backBtnText: {
    fontSize: 13,
    color: '#4F46E5',
    fontWeight: '700',
  },
  titleCard: {
    backgroundColor: '#0B132B',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
  },
  screenEmoji: {
    fontSize: 32,
    marginBottom: 6,
  },
  screenTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '900',
  },
  screenSubtitle: {
    color: '#9CA3AF',
    fontSize: 12,
    marginTop: 4,
    textAlign: 'center',
  },
  ocrBox: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 16,
  },
  ocrHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ocrTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#111827',
    flex: 1,
  },
  ocrToggleBtn: {
    backgroundColor: '#ECFDF5',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#047857',
  },
  ocrToggleText: {
    color: '#047857',
    fontSize: 11,
    fontWeight: '700',
  },
  privacyNote: {
    fontSize: 10,
    color: '#047857',
    backgroundColor: '#F0FDF4',
    padding: 8,
    borderRadius: 8,
    marginTop: 8,
  },
  ocrContent: {
    marginTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
    paddingTop: 10,
  },
  ocrHelper: {
    fontSize: 11,
    color: '#6B7280',
    marginBottom: 6,
  },
  templateButtonsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  templateChip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: '#F3F4F6',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  templateChipActive: {
    backgroundColor: '#047857',
    borderColor: '#047857',
  },
  templateChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#4B5563',
  },
  templateChipTextActive: {
    color: '#FFFFFF',
  },
  ocrInput: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 10,
    padding: 10,
    fontSize: 11,
    fontFamily: 'monospace',
    height: 70,
    marginBottom: 10,
  },
  ocrScanBtn: {
    backgroundColor: '#0B132B',
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  ocrScanBtnText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  ocrResultCard: {
    backgroundColor: '#F0FDF4',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#BBF7D0',
    marginTop: 10,
  },
  ocrResultTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#065F46',
    marginBottom: 4,
  },
  ocrResultField: {
    fontSize: 11,
    color: '#374151',
    lineHeight: 16,
  },
  ocrResultSource: {
    fontSize: 10,
    color: '#059669',
    marginTop: 4,
    fontFamily: 'monospace',
  },
  bold: {
    fontWeight: '800',
    color: '#111827',
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 4,
    marginTop: 10,
  },
  input: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13,
    color: '#111827',
  },
  monoInput: {
    fontFamily: 'monospace',
    fontWeight: '700',
  },
  submitBtn: {
    backgroundColor: '#047857',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
    shadowColor: '#047857',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 5,
    elevation: 3,
  },
  submitBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  errorBox: {
    backgroundColor: '#FEF2F2',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FECACA',
    marginBottom: 10,
  },
  errorText: {
    color: '#DC2626',
    fontSize: 12,
  },
  successCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 24,
    borderWidth: 1,
    borderColor: '#10B981',
    alignItems: 'center',
  },
  successEmoji: {
    fontSize: 40,
    marginBottom: 8,
  },
  successTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: '#065F46',
    textAlign: 'center',
  },
  successSubtitle: {
    fontSize: 12,
    color: '#4B5563',
    textAlign: 'center',
    marginTop: 4,
    marginBottom: 16,
  },
  credentialBox: {
    backgroundColor: '#0B132B',
    padding: 18,
    borderRadius: 14,
    width: '100%',
    alignItems: 'center',
    marginBottom: 16,
  },
  credentialLabel: {
    color: '#9CA3AF',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  credentialCode: {
    color: '#34D399',
    fontSize: 20,
    fontWeight: '900',
    fontFamily: 'monospace',
    letterSpacing: 1.5,
    marginVertical: 8,
  },
  credentialWarning: {
    color: '#FCD34D',
    fontSize: 10,
    textAlign: 'center',
  },
  goToBoothBtn: {
    backgroundColor: '#047857',
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
  },
  goToBoothBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
});
