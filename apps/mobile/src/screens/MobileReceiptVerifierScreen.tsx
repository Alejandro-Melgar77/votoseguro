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
import { mobileApi } from '../api/mobile-client';
import {
  ReceiptVerificationResponse,
  MerkleInclusionProofResponse,
  MerkleVerifyResponse,
} from '@votoseguro/api-client';

interface MobileReceiptVerifierScreenProps {
  initialReceiptHash?: string;
  initialElectionId?: string;
  onNavigate: (screen: 'home' | 'register' | 'booth' | 'receipt' | 'faq', params?: any) => void;
}

export const MobileReceiptVerifierScreen: React.FC<MobileReceiptVerifierScreenProps> = ({
  initialReceiptHash = '',
  initialElectionId = '',
  onNavigate,
}) => {
  const [tab, setTab] = useState<'receipt' | 'merkle'>('receipt');

  // Estado Verificador de Recibo (S2-03)
  const [receiptHash, setReceiptHash] = useState(initialReceiptHash);
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [receiptError, setReceiptError] = useState<string | null>(null);
  const [receiptData, setReceiptData] = useState<ReceiptVerificationResponse | null>(null);

  // Estado Árbol de Merkle (S2-07)
  const [electionId, setElectionId] = useState(initialElectionId);
  const [documentId, setDocumentId] = useState('');
  const [merkleLoading, setMerkleLoading] = useState(false);
  const [merkleError, setMerkleError] = useState<string | null>(null);
  const [merkleProof, setMerkleProof] = useState<MerkleInclusionProofResponse | null>(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<MerkleVerifyResponse | null>(null);

  useEffect(() => {
    if (initialReceiptHash) {
      handleVerifyReceipt();
    }
  }, [initialReceiptHash]);

  const handleVerifyReceipt = async () => {
    if (!receiptHash.trim()) {
      setReceiptError('Por favor ingrese el código o hash de comprobante electoral.');
      return;
    }

    setReceiptLoading(true);
    setReceiptError(null);
    setReceiptData(null);

    try {
      const data = await mobileApi.get<ReceiptVerificationResponse>(
        `/receipts/${encodeURIComponent(receiptHash.trim())}`
      );
      setReceiptData(data);
      if (data.election_id && !electionId) {
        setElectionId(data.election_id);
      }
    } catch (err: any) {
      setReceiptError(err.message || 'No se encontró el comprobante en la urna criptográfica.');
    } finally {
      setReceiptLoading(false);
    }
  };

  const handleFetchMerkleProof = async () => {
    if (!electionId.trim() || !documentId.trim()) {
      setMerkleError('Ingrese el ID de la elección y su número de Cédula (CI).');
      return;
    }

    setMerkleLoading(true);
    setMerkleError(null);
    setMerkleProof(null);
    setVerifyResult(null);

    try {
      const data = await mobileApi.get<MerkleInclusionProofResponse>(
        `/elections/${electionId.trim()}/merkle/proof/${encodeURIComponent(documentId.trim())}`
      );
      setMerkleProof(data);
    } catch (err: any) {
      setMerkleError(
        err.message || 'No se pudo obtener la prueba de Merkle para el documento indicado.'
      );
    } finally {
      setMerkleLoading(false);
    }
  };

  const handleVerifyMerkleProof = async () => {
    if (!merkleProof || !electionId.trim()) return;

    setVerifyLoading(true);
    try {
      const result = await mobileApi.post<MerkleVerifyResponse>(
        `/elections/${electionId.trim()}/merkle/verify`,
        {
          leaf_hash: merkleProof.leaf_hash,
          merkle_root: merkleProof.merkle_root,
          proof: merkleProof.proof,
        }
      );
      setVerifyResult(result);
    } catch (err: any) {
      Alert.alert('Error de verificación', err.message || 'Fallo matemático en la verificación.');
    } finally {
      setVerifyLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Barra superior de navegación */}
        <View style={styles.navRow}>
          <TouchableOpacity onPress={() => onNavigate('home')} style={styles.backButton}>
            <Text style={styles.backButtonText}>← Volver al Portal</Text>
          </TouchableOpacity>
        </View>

        {/* Encabezado Cívico */}
        <View style={styles.headerBox}>
          <View style={styles.badgeRow}>
            <View style={styles.securityBadge}>
              <Text style={styles.securityBadgeText}>⛓️ AUDITORÍA CRIPTOGRÁFICA</Text>
            </View>
          </View>
          <Text style={styles.title}>Verificador Cívico de Comprobantes</Text>
          <Text style={styles.subtitle}>
            Audite la inclusión inmutable de su voto en la urna (S2-03) y la integridad del padrón
            mediante Árboles de Merkle (S2-07).
          </Text>
        </View>

        {/* Selector de Pestaña */}
        <View style={styles.tabsContainer}>
          <TouchableOpacity
            style={[styles.tabButton, tab === 'receipt' && styles.tabButtonActive]}
            onPress={() => setTab('receipt')}
          >
            <Text style={[styles.tabText, tab === 'receipt' && styles.tabTextActive]}>
              📜 Comprobante de Urna
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tabButton, tab === 'merkle' && styles.tabButtonActive]}
            onPress={() => setTab('merkle')}
          >
            <Text style={[styles.tabText, tab === 'merkle' && styles.tabTextActive]}>
              🌳 Padrón Merkle
            </Text>
          </TouchableOpacity>
        </View>

        {/* =================================================================== */}
        {/* PESTAÑA 1: VERIFICADOR DE COMPROBANTE EN URNA (S2-03) */}
        {/* =================================================================== */}
        {tab === 'receipt' && (
          <View>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Búsqueda de Comprobante Electoral</Text>
              <Text style={styles.cardDesc}>
                Ingrese la huella SHA-256 (receipt_hash) entregada al emitir su voto.
              </Text>

              <TextInput
                style={[styles.textInput, styles.codeFont]}
                value={receiptHash}
                onChangeText={setReceiptHash}
                placeholder="Pegue aquí su receipt_hash..."
                placeholderTextColor="#9CA3AF"
                autoCapitalize="none"
              />

              <TouchableOpacity
                style={[styles.primaryButton, receiptLoading && styles.buttonDisabled]}
                onPress={handleVerifyReceipt}
                disabled={receiptLoading}
              >
                {receiptLoading ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text style={styles.primaryButtonText}>🔍 Verificar Voto en Urna</Text>
                )}
              </TouchableOpacity>
            </View>

            {receiptError && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>⚠️ {receiptError}</Text>
              </View>
            )}

            {receiptData && (
              <View style={styles.resultCard}>
                <View style={styles.resultBadgeRow}>
                  <View
                    style={[
                      styles.statusBadge,
                      receiptData.verified ? styles.statusBadgeValid : styles.statusBadgeInvalid,
                    ]}
                  >
                    <Text
                      style={[
                        styles.statusBadgeText,
                        receiptData.verified
                          ? styles.statusBadgeTextValid
                          : styles.statusBadgeTextInvalid,
                      ]}
                    >
                      {receiptData.verified ? '✓ COMPROBANTE SELLADO EN URNA' : '⚠️ NO VERIFICADO'}
                    </Text>
                  </View>
                </View>

                <Text style={styles.resultTitle}>{receiptData.election_name}</Text>
                {receiptData.organization_name && (
                  <Text style={styles.resultOrg}>{receiptData.organization_name}</Text>
                )}

                <View style={styles.divider} />

                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Huella Hash Auditada:</Text>
                  <Text style={styles.detailHash}>{receiptData.receipt_hash}</Text>
                </View>

                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Minuto de Registro:</Text>
                  <Text style={styles.detailValue}>{receiptData.cast_at_minute}</Text>
                </View>

                {receiptData.total_votes_in_ballot !== undefined && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Cargos Sufragados:</Text>
                    <Text style={styles.detailValue}>
                      {receiptData.total_votes_in_ballot} selecciones registradas
                    </Text>
                  </View>
                )}

                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Integridad de la Cadena de Hashes:</Text>
                  <Text
                    style={[
                      styles.detailValue,
                      { color: receiptData.chain_intact ? '#047857' : '#DC2626' },
                    ]}
                  >
                    {receiptData.chain_intact
                      ? '✓ Eslabón Intacto (SHA-256 inmutable)'
                      : '⚠️ Enlace con discrepancia'}
                  </Text>
                </View>

                {/* Prueba de Cadena de Hashes */}
                {receiptData.chain_proof && receiptData.chain_proof.length > 0 && (
                  <View style={styles.proofContainer}>
                    <Text style={styles.proofTitle}>
                      Secuencia en Cadena de Urna ({receiptData.chain_proof.length} bloques):
                    </Text>
                    {receiptData.chain_proof.map((cp) => (
                      <View key={cp.chain_index} style={styles.proofStep}>
                        <Text style={styles.proofStepNum}>Bloque #{cp.chain_index}</Text>
                        <Text style={styles.proofStepHash}>Hash: {cp.vote_hash.slice(0, 18)}...</Text>
                        <Text style={styles.proofStepPrev}>
                          Prev: {cp.prev_hash ? `${cp.prev_hash.slice(0, 18)}...` : 'GÉNESIS'}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}

                <View style={styles.civicGuarantee}>
                  <Text style={styles.civicGuaranteeText}>
                    🛡️ Garantía de Secreto: Esta consulta verifica que su voto está contabilizado en
                    la urna sin comprometer el secreto del sufragio (Invariante #9).
                  </Text>
                </View>
              </View>
            )}
          </View>
        )}

        {/* =================================================================== */}
        {/* PESTAÑA 2: PRUEBA DE INCLUSIÓN EN ÁRBOL DE MERKLE (S2-07) */}
        {/* =================================================================== */}
        {tab === 'merkle' && (
          <View>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Inclusión en Padrón Congelado</Text>
              <Text style={styles.cardDesc}>
                Obtenga la ruta criptográfica de su hoja en el Árbol de Merkle del padrón electoral
                congelado sin revelar la identidad de los demás votantes.
              </Text>

              <Text style={styles.fieldLabel}>ID de la Elección</Text>
              <TextInput
                style={[styles.textInput, styles.codeFont]}
                value={electionId}
                onChangeText={setElectionId}
                placeholder="UUID de la elección..."
                placeholderTextColor="#9CA3AF"
                autoCapitalize="none"
              />

              <Text style={[styles.fieldLabel, { marginTop: 12 }]}>
                Cédula de Identidad del Elector (CI)
              </Text>
              <TextInput
                style={styles.textInput}
                value={documentId}
                onChangeText={setDocumentId}
                placeholder="Ej. 8001002"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />

              <TouchableOpacity
                style={[styles.primaryButton, merkleLoading && styles.buttonDisabled]}
                onPress={handleFetchMerkleProof}
                disabled={merkleLoading}
              >
                {merkleLoading ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text style={styles.primaryButtonText}>🌳 Consultar Prueba de Merkle</Text>
                )}
              </TouchableOpacity>
            </View>

            {merkleError && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>⚠️ {merkleError}</Text>
              </View>
            )}

            {merkleProof && (
              <View style={styles.resultCard}>
                <Text style={styles.resultTitle}>Prueba Criptográfica de Inclusión</Text>
                <Text style={styles.resultOrg}>
                  Padrón Congelado: {merkleProof.is_frozen !== false ? 'SÍ (Inmutable)' : 'NO'}
                </Text>

                <View style={styles.divider} />

                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Hash de la Hoja del Elector (Leaf):</Text>
                  <Text style={styles.detailHash}>{merkleProof.leaf_hash}</Text>
                </View>

                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Raíz Oficial de Merkle (Merkle Root):</Text>
                  <Text style={styles.detailHash}>{merkleProof.merkle_root}</Text>
                </View>

                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>Longitud del Camino de Prueba:</Text>
                  <Text style={styles.detailValue}>
                    {merkleProof.proof.length} niveles logarítmicos
                  </Text>
                </View>

                <TouchableOpacity
                  style={[styles.verifyProofButton, verifyLoading && styles.buttonDisabled]}
                  onPress={handleVerifyMerkleProof}
                  disabled={verifyLoading}
                >
                  {verifyLoading ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <Text style={styles.verifyProofButtonText}>
                      ⚡ Reconstruir Matemáticamente la Raíz
                    </Text>
                  )}
                </TouchableOpacity>

                {verifyResult && (
                  <View
                    style={[
                      styles.verifyResultBox,
                      (verifyResult.valid ?? verifyResult.is_valid)
                        ? styles.verifyResultBoxValid
                        : styles.verifyResultBoxInvalid,
                    ]}
                  >
                    <Text
                      style={[
                        styles.verifyResultText,
                        (verifyResult.valid ?? verifyResult.is_valid)
                          ? styles.verifyResultTextValid
                          : styles.verifyResultTextInvalid,
                      ]}
                    >
                      {(verifyResult.valid ?? verifyResult.is_valid)
                        ? '✓ Raíz Reconstruida con Precisión Matemática (Padrón Fidedigno)'
                        : '⚠️ Discrepancia Criptográfica: la raíz calculada no coincide'}
                    </Text>
                    <Text style={styles.proofStepPrev}>
                      Calculada: {(verifyResult.computed_root || verifyResult.calculated_root || '').slice(0, 24)}...
                    </Text>
                  </View>
                )}
              </View>
            )}
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
    marginBottom: 20,
  },
  badgeRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  securityBadge: {
    backgroundColor: 'rgba(79, 70, 229, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#4F46E5',
  },
  securityBadgeText: {
    color: '#4F46E5',
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
  tabsContainer: {
    flexDirection: 'row',
    backgroundColor: '#E5E7EB',
    borderRadius: 14,
    padding: 4,
    marginBottom: 16,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  tabButtonActive: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  tabText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#6B7280',
  },
  tabTextActive: {
    color: '#111827',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 4,
  },
  cardDesc: {
    fontSize: 12,
    color: '#6B7280',
    lineHeight: 16,
    marginBottom: 14,
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 4,
  },
  textInput: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#111827',
    marginBottom: 14,
  },
  codeFont: {
    fontFamily: 'monospace',
    fontSize: 12,
  },
  primaryButton: {
    backgroundColor: '#047857',
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: 'center',
  },
  primaryButtonText: {
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
  resultCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginBottom: 20,
  },
  resultBadgeRow: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
  },
  statusBadgeValid: {
    backgroundColor: '#ECFDF5',
    borderColor: '#047857',
  },
  statusBadgeInvalid: {
    backgroundColor: '#FEF2F2',
    borderColor: '#DC2626',
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: '800',
  },
  statusBadgeTextValid: {
    color: '#047857',
  },
  statusBadgeTextInvalid: {
    color: '#DC2626',
  },
  resultTitle: {
    fontSize: 17,
    fontWeight: '900',
    color: '#111827',
  },
  resultOrg: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E7EB',
    marginVertical: 14,
  },
  detailItem: {
    marginBottom: 10,
  },
  detailLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B7280',
  },
  detailHash: {
    fontSize: 11,
    color: '#1F2937',
    fontFamily: 'monospace',
    backgroundColor: '#F3F4F6',
    padding: 6,
    borderRadius: 6,
    marginTop: 3,
  },
  detailValue: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
    marginTop: 2,
  },
  proofContainer: {
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    padding: 10,
    marginTop: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  proofTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#334155',
    marginBottom: 6,
  },
  proofStep: {
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
    paddingVertical: 4,
  },
  proofStepNum: {
    fontSize: 10,
    fontWeight: '800',
    color: '#64748B',
  },
  proofStepHash: {
    fontSize: 10,
    fontFamily: 'monospace',
    color: '#0F172A',
  },
  proofStepPrev: {
    fontSize: 10,
    fontFamily: 'monospace',
    color: '#64748B',
  },
  civicGuarantee: {
    backgroundColor: '#F0FDF4',
    padding: 10,
    borderRadius: 8,
    marginTop: 14,
  },
  civicGuaranteeText: {
    fontSize: 11,
    color: '#166534',
    lineHeight: 15,
  },
  verifyProofButton: {
    backgroundColor: '#4F46E5',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  verifyProofButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
  verifyResultBox: {
    borderRadius: 10,
    padding: 10,
    marginTop: 10,
    borderWidth: 1,
  },
  verifyResultBoxValid: {
    backgroundColor: '#ECFDF5',
    borderColor: '#34D399',
  },
  verifyResultBoxInvalid: {
    backgroundColor: '#FEF2F2',
    borderColor: '#F87171',
  },
  verifyResultText: {
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 4,
  },
  verifyResultTextValid: {
    color: '#047857',
  },
  verifyResultTextInvalid: {
    color: '#DC2626',
  },
});
