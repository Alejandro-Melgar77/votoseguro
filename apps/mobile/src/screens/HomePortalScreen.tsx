import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
} from 'react-native';

interface HomePortalScreenProps {
  onNavigate: (screen: 'home' | 'register' | 'booth' | 'receipt' | 'faq', params?: any) => void;
}

export const HomePortalScreen: React.FC<HomePortalScreenProps> = ({ onNavigate }) => {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0B132B" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Cabecera Cívica */}
        <View style={styles.headerCard}>
          <View style={styles.badgeRow}>
            <View style={styles.securityBadge}>
              <Text style={styles.securityBadgeText}>🔐 CRIPTOGRÁFICAMENTE AUDITADO</Text>
            </View>
          </View>
          <Text style={styles.headerTitle}>VotoSeguro Mobile</Text>
          <Text style={styles.headerSubtitle}>
            SaaS Multi-Institución de Votación Electrónica Soberana (v2.0)
          </Text>
          <Text style={styles.headerMeta}>
            Padrón Criptográfico • Sufragio Ciego Atómico • IA Local LFM3-1.7B
          </Text>
        </View>

        {/* Acciones Principales */}
        <View style={styles.menuContainer}>
          {/* 1. Registro y Activación */}
          <TouchableOpacity
            style={styles.actionCard}
            onPress={() => onNavigate('register')}
            activeOpacity={0.8}
          >
            <View style={[styles.cardIconBox, { backgroundColor: '#EEF2FF' }]}>
              <Text style={styles.cardEmoji}>🪪</Text>
            </View>
            <View style={styles.cardContent}>
              <Text style={styles.cardTitle}>Registro y Activación de Elector</Text>
              <Text style={styles.cardDescription}>
                Activación por enlace único, deep link (votoseguro://) y escáner OCR de cédula local (IA-L3).
              </Text>
              <Text style={styles.cardLinkText}>Comenzar activación →</Text>
            </View>
          </TouchableOpacity>

          {/* 2. Cabina de Votación */}
          <TouchableOpacity
            style={[styles.actionCard, styles.actionCardPrimary]}
            onPress={() => onNavigate('booth')}
            activeOpacity={0.8}
          >
            <View style={[styles.cardIconBox, { backgroundColor: '#ECFDF5' }]}>
              <Text style={styles.cardEmoji}>🗳️</Text>
            </View>
            <View style={styles.cardContent}>
              <Text style={[styles.cardTitle, { color: '#0B132B' }]}>
                Cabina de Votación Accesible (IA-L4)
              </Text>
              <Text style={styles.cardDescription}>
                Ingreso con CI + credencial VS, papeleta automática por estamento y comandos de voz locales.
              </Text>
              <Text style={[styles.cardLinkText, { color: '#047857' }]}>
                Ingresar a sufragar →
              </Text>
            </View>
          </TouchableOpacity>

          {/* 3. Verificador de Recibos y Merkle */}
          <TouchableOpacity
            style={styles.actionCard}
            onPress={() => onNavigate('receipt')}
            activeOpacity={0.8}
          >
            <View style={[styles.cardIconBox, { backgroundColor: '#F0FDF4' }]}>
              <Text style={styles.cardEmoji}>📜</Text>
            </View>
            <View style={styles.cardContent}>
              <Text style={styles.cardTitle}>Verificación de Comprobante (S2-03)</Text>
              <Text style={styles.cardDescription}>
                Audite su receipt_hash en la cadena de votos y valide su inclusión con Árbol de Merkle (S2-07).
              </Text>
              <Text style={styles.cardLinkText}>Verificar voto en urna →</Text>
            </View>
          </TouchableOpacity>

          {/* 4. Asistente Electoral RAG */}
          <TouchableOpacity
            style={styles.actionCard}
            onPress={() => onNavigate('faq')}
            activeOpacity={0.8}
          >
            <View style={[styles.cardIconBox, { backgroundColor: '#FEF3C7' }]}>
              <Text style={styles.cardEmoji}>🤖</Text>
            </View>
            <View style={styles.cardContent}>
              <Text style={styles.cardTitle}>Asistente Electoral Oficial (IA-L5)</Text>
              <Text style={styles.cardDescription}>
                Consultas operativas con RAG sobre los 12 manuales de VotoSeguro con citas textuales verificables.
              </Text>
              <Text style={[styles.cardLinkText, { color: '#B45309' }]}>
                Hacer una consulta →
              </Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* Footer Institucional */}
        <View style={styles.footerContainer}>
          <Text style={styles.footerTitle}>VotoSeguro v2.0 • Release Oficial</Text>
          <Text style={styles.footerText}>
            Universidad Autónoma Gabriel René Moreno (UAGRM) — INF 422 SB
          </Text>
          <Text style={styles.footerSubtext}>
            Invariantes de secreto absoluto (#9), nullifier HMAC (#8) y cadena de hashes (#19).
          </Text>
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
  headerCard: {
    backgroundColor: '#0B132B',
    borderRadius: 20,
    padding: 24,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 10,
    elevation: 4,
  },
  badgeRow: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  securityBadge: {
    backgroundColor: 'rgba(4, 120, 87, 0.25)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#047857',
  },
  securityBadgeText: {
    color: '#34D399',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 26,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  headerSubtitle: {
    color: '#9CA3AF',
    fontSize: 13,
    fontWeight: '600',
    marginTop: 4,
  },
  headerMeta: {
    color: '#6EE7B7',
    fontSize: 11,
    marginTop: 10,
    fontFamily: 'monospace',
  },
  menuContainer: {
    gap: 14,
  },
  actionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 18,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  actionCardPrimary: {
    borderColor: '#047857',
    borderWidth: 1.5,
    backgroundColor: '#FDFBF7',
  },
  cardIconBox: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  cardEmoji: {
    fontSize: 24,
  },
  cardContent: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 3,
  },
  cardDescription: {
    fontSize: 11,
    color: '#6B7280',
    lineHeight: 16,
    marginBottom: 6,
  },
  cardLinkText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4F46E5',
  },
  footerContainer: {
    marginTop: 32,
    alignItems: 'center',
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  footerTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: '#374151',
  },
  footerText: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 2,
  },
  footerSubtext: {
    fontSize: 10,
    color: '#9CA3AF',
    textAlign: 'center',
    marginTop: 4,
    paddingHorizontal: 20,
  },
});
