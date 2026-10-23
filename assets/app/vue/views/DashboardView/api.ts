import { useAuthFetch } from "@/composables/useFetch";
import type {
  AppPasswordApiResponse,
  AppPasswordCreateResponse,
  AppPasswordListResponse,
  AppPasswordRevokeResponse,
} from './types';

interface SettingsApiResponse {
  success: boolean;
  message?: string;
  error?: string;
  app_password?: string;
}

const APP_PASSWORDS_URL = '/api/v1/mail/app-passwords/';

/** Parse a JSON body and tag it with the HTTP status; a non-JSON reply (proxy error page) becomes a thrown Error. */
const readAppPasswordResponse = async <T extends AppPasswordApiResponse>(response: Response): Promise<T> => {
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error(response.statusText || `HTTP ${response.status}`);
  }
  const data = await response.json();
  return { ...data, status: response.status } as T;
};

export const listAppPasswords = async (): Promise<AppPasswordListResponse> => {
  const { response } = await useAuthFetch(APP_PASSWORDS_URL, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  return readAppPasswordResponse<AppPasswordListResponse>(response.value);
};

export const createAppPassword = async (name: string): Promise<AppPasswordCreateResponse> => {
  const { response } = await useAuthFetch(`${APP_PASSWORDS_URL}create/`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ name }),
  });

  return readAppPasswordResponse<AppPasswordCreateResponse>(response.value);
};

export const revokeAppPassword = async (id: string): Promise<AppPasswordRevokeResponse> => {
  const { response } = await useAuthFetch(`${APP_PASSWORDS_URL}${encodeURIComponent(id)}/revoke/`, {
    method: 'DELETE',
    headers: {
      'Accept': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
  });

  return readAppPasswordResponse<AppPasswordRevokeResponse>(response.value);
};

export const setAppPassword = async (name: string, password: string): Promise<SettingsApiResponse> => {
  const { response } = await useAuthFetch('/api/v1/mail/app-passwords/set/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ name, password }),
  });

  return await response.value.json();
};

export const setDisplayName = async (displayName: string): Promise<SettingsApiResponse> => {
  const { response } = await useAuthFetch('/api/v1/mail/display-name/set/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'display-name': displayName }),
  });

  return await response.value.json();
};

export const getSubscriptionPlanInfo = async () => {
  const { response } = await useAuthFetch('/api/v1/subscription/plan/info/', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  // If we're not getting a application/json response then return the status text
  if (!response.value.headers.get('content-type')?.includes('application/json')) {
    throw new Error(response.value.statusText);
  }

  return await response.value.json();
}

export const getSendStorageInfo = async () => {
  const { response } = await useAuthFetch('/api/v1/subscription/send/storage/', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  // If we're not getting a application/json response then return the status text
  if (!response.value.headers.get('content-type')?.includes('application/json')) {
    throw new Error(response.value.statusText);
  }

  return await response.value.json();
}
