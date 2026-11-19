import { describe, expect, it } from 'vitest';
import { keycloakUrlForHostname } from './defines';

describe('keycloakUrlForHostname', () => {
  it.each([
    ['accounts.tb.pro', 'https://auth.tb.pro'],
    ['accounts.stage-thundermail.com', 'https://auth.stage-thundermail.com'],
    ['localhost', 'http://keycloak:8999'],
  ])('maps %s to %s', (hostname, url) => {
    expect(keycloakUrlForHostname(hostname)).toBe(url);
  });
});
