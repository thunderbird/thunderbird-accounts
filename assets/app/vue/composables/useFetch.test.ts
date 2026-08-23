import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthRedirectError, AuthSessionError, useAuthFetch } from './useFetch';

describe('useAuthFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('adds the default Accept header and preserves request options', async () => {
    const response = new Response('{}', { status: 200 });
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);

    const result = await useAuthFetch('/api/example', {
      method: 'POST',
      headers: { 'X-CSRFToken': 'csrf-token' },
    });

    const options = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(options.headers);
    expect(result.response.value).toBe(response);
    expect(options.method).toBe('POST');
    expect(headers.get('Accept')).toBe('application/json');
    expect(headers.get('X-CSRFToken')).toBe('csrf-token');
  });

  it('starts reauthentication and rejects instead of resuming the caller', async () => {
    const assign = vi.fn();
    vi.stubGlobal('window', { location: { assign } });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ type: 'auth_error', refresh_url: '/oidc/authenticate/' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(useAuthFetch('/api/example')).rejects.toBeInstanceOf(AuthRedirectError);
    expect(assign).toHaveBeenCalledWith('/oidc/authenticate/');
  });

  it('rejects auth errors that cannot redirect', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ type: 'auth_error', error: 'Session expired' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(useAuthFetch('/api/example')).rejects.toEqual(new AuthSessionError('Session expired'));
  });

  it('preserves non-session 403 responses', async () => {
    const response = new Response(JSON.stringify({ reauthUrl: '/oidc/mfa-reauth/' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));

    const result = await useAuthFetch('/api/example');
    expect(result.response.value).toBe(response);
  });
});
