import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth-store';
import { PublicLandingRequestPage } from '@/pages/PublicLandingRequestPage';
import { LoginPage } from '@/pages/LoginPage';
import { PlatformAdminConsolePage } from '@/pages/PlatformAdminConsolePage';
import { ElectionWorkspacePage } from '@/pages/ElectionWorkspacePage';
import { ScheduleControlPanelPage } from '@/pages/ScheduleControlPanelPage';
import { DelegateAdminsPage } from '@/pages/DelegateAdminsPage';
import { StructureArchitectPage } from '@/pages/StructureArchitectPage';
import { CandidatesBallotStudioPage } from '@/pages/CandidatesBallotStudioPage';
import { VoterRollRegistrationPanelPage } from '@/pages/VoterRollRegistrationPanelPage';
import { PublicVoterRegistrationPage } from '@/pages/PublicVoterRegistrationPage';
import { VoterBallotBoothPage } from '@/pages/VoterBallotBoothPage';
import { ElectionResultsTallyPage } from '@/pages/ElectionResultsTallyPage';
import { LiveMonitoringDashboardPage } from '@/pages/LiveMonitoringDashboardPage';
import { CryptographicIntegrityCenterPage } from '@/pages/CryptographicIntegrityCenterPage';
import { PublicReceiptVerifierPage } from '@/pages/PublicReceiptVerifierPage';
import { PublicSelfRegistrationPage } from '@/pages/PublicSelfRegistrationPage';

const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  allowedRoles?: string[];
}> = ({ children, allowedRoles }) => {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    if (user.role === 'PLATFORM_ADMIN') {
      return <Navigate to="/platform/console" replace />;
    }
    return <Navigate to="/workspace" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Rutas Públicas */}
        <Route path="/" element={<PublicLandingRequestPage />} />
        <Route path="/request-election" element={<PublicLandingRequestPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register/:token" element={<PublicVoterRegistrationPage />} />
        <Route path="/vote" element={<VoterBallotBoothPage />} />
        <Route path="/verify-receipt" element={<PublicReceiptVerifierPage />} />
        <Route path="/verify-receipt/:receiptHash" element={<PublicReceiptVerifierPage />} />
        <Route path="/elections/:electionId/self-register" element={<PublicSelfRegistrationPage />} />

        {/* Consola de Operador de Plataforma */}
        <Route
          path="/platform/console"
          element={
            <ProtectedRoute allowedRoles={['PLATFORM_ADMIN']}>
              <PlatformAdminConsolePage />
            </ProtectedRoute>
          }
        />

        {/* Espacio Institucional de Elecciones */}
        <Route
          path="/workspace"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT']}>
              <ElectionWorkspacePage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/structure"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL']}>
              <StructureArchitectPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/candidates"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL']}>
              <CandidatesBallotStudioPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/voters"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT']}>
              <VoterRollRegistrationPanelPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/schedule"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT']}>
              <ScheduleControlPanelPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/delegates"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT']}>
              <DelegateAdminsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/live"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT', 'OBSERVER']}>
              <LiveMonitoringDashboardPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/results"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT', 'OBSERVER']}>
              <ElectionResultsTallyPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/elections/:electionId/integrity"
          element={
            <ProtectedRoute allowedRoles={['ADMIN_GENERAL', 'ADMIN_SEGMENT', 'OBSERVER']}>
              <CryptographicIntegrityCenterPage />
            </ProtectedRoute>
          }
        />

        {/* Redirección por defecto */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
