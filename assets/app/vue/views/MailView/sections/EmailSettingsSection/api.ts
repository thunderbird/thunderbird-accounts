import { useAuthFetch } from "@/composables/useFetch";

interface SettingsApiResponse {
  success: boolean;
  message?: string;
  error?: string;
}

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

export const addEmailAlias = async (emailAlias: string, domain: string) => {
  const { response } = await useAuthFetch(`/email-aliases/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'email-alias': emailAlias, 'domain': domain }),
  });

  return await response.value.json();
};

export const removeEmailAlias = async (emailAlias: string) => {
  const { response } = await useAuthFetch(`/email-aliases/remove`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'email-alias': emailAlias }),
  });

  return await response.value.json();
};
