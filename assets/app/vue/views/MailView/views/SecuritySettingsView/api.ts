import type { ActiveSession } from './types';

const parseJsonResponse = async <T>(response: Response): Promise<T> => {
  const data = await response.json();

  if (!response.ok || data.success === false) {
    throw new Error(data.error || data.detail || response.statusText);
  }

  return data;
};

export const getActiveSessions = async () => {
  const response = await fetch('/api/v1/auth/get-active-sessions/', {
    method: 'GET',
    credentials: 'include',
  });

  return parseJsonResponse<ActiveSession[]>(response);
}

export const signOutSession = async (sessionId: string) => {
  const response = await fetch('/api/v1/auth/sign-out-session/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  return parseJsonResponse<{ success: boolean }>(response);
}

export const signOutAllSessions = async () => {
  const activeSessions = await getActiveSessions();
  const orderedSessions = [...activeSessions].sort((a, b) => Number(a.is_current) - Number(b.is_current));

  return await Promise.all(orderedSessions.map((session) => signOutSession(session.id)));
}
