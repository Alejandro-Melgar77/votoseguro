/**
 * Gestor de Estado de Autenticación y Tenant Activo
 */
import { useState, useEffect } from 'react';
import type { User, Organization } from '@votoseguro/api-client';

export interface AuthState {
  token: string | null;
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

let globalListeners: Array<() => void> = [];

function notifyListeners() {
  globalListeners.forEach((listener) => listener());
}

export function setAuthSession(token: string, user: User, organization: Organization | null) {
  localStorage.setItem('votoseguro_token', token);
  localStorage.setItem('votoseguro_user', JSON.stringify(user));
  if (organization) {
    localStorage.setItem('votoseguro_org', JSON.stringify(organization));
  } else {
    localStorage.removeItem('votoseguro_org');
  }
  notifyListeners();
}

export function clearAuthSession() {
  localStorage.removeItem('votoseguro_token');
  localStorage.removeItem('votoseguro_user');
  localStorage.removeItem('votoseguro_org');
  notifyListeners();
}

export function useAuth() {
  const [state, setState] = useState<AuthState>(() => {
    const token = localStorage.getItem('votoseguro_token');
    const userStr = localStorage.getItem('votoseguro_user');
    const orgStr = localStorage.getItem('votoseguro_org');

    return {
      token,
      user: userStr ? JSON.parse(userStr) : null,
      organization: orgStr ? JSON.parse(orgStr) : null,
      isAuthenticated: !!token,
      isLoading: false,
    };
  });

  useEffect(() => {
    const syncState = () => {
      const token = localStorage.getItem('votoseguro_token');
      const userStr = localStorage.getItem('votoseguro_user');
      const orgStr = localStorage.getItem('votoseguro_org');

      setState({
        token,
        user: userStr ? JSON.parse(userStr) : null,
        organization: orgStr ? JSON.parse(orgStr) : null,
        isAuthenticated: !!token,
        isLoading: false,
      });
    };

    globalListeners.push(syncState);
    return () => {
      globalListeners = globalListeners.filter((l) => l !== syncState);
    };
  }, []);

  return {
    ...state,
    logout: clearAuthSession,
    isPlatformAdmin: state.user?.role === 'PLATFORM_ADMIN',
    isAdminGeneral: state.user?.role === 'ADMIN_GENERAL',
    isAdminSegment: state.user?.role === 'ADMIN_SEGMENT',
  };
}
