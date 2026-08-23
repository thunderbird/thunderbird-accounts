import { createFetch } from '@vueuse/core';

interface AuthenticationErrorResponse {
  error?: string;
  type?: string;
  refresh_url?: string;
}

export class AuthRedirectError extends Error {
  constructor() {
    super('Redirecting to authentication');
    this.name = 'AuthRedirectError';
  }
}

export class AuthSessionError extends Error {
  constructor(message = 'The authentication session has expired') {
    super(message);
    this.name = 'AuthSessionError';
  }
}

const useAuthFetchRequest = createFetch({
  options: {
    async beforeFetch(ctx) {
      // JSON auth failures include a refresh URL instead of redirecting the fetch request.
      if (!ctx.options.headers['Accept']) {
        ctx.options.headers['Accept'] = 'application/json';
      }
      return ctx;
    },
  },
  fetchOptions: {
    mode: 'cors',
  },
});

export const useAuthFetch = async (url: string, options: RequestInit = {}) => {
  const result = await useAuthFetchRequest(url, options);
  const response = result.response.value;
  if (!response) {
    throw new Error(result.error.value || 'Request failed');
  }

  // VueUse stores HTTP errors in reactive state, so session failures must be handled explicitly.
  if (response.status !== 403) {
    return result;
  }

  const data = (await response
    .clone()
    .json()
    .catch(() => null)) as AuthenticationErrorResponse | null;
  if (data?.type !== 'auth_error') {
    // Feature-specific 403 responses, including MFA reauthentication, stay with their callers.
    return result;
  }

  if (data.refresh_url) {
    window.location.assign(data.refresh_url);
    // Prevent the caller from consuming the 403 after navigation starts.
    throw new AuthRedirectError();
  }

  throw new AuthSessionError(data.error);
};
