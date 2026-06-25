import {
  ACCTS_OIDC_EMAIL,
  KEYCLOAK_ADMIN_BASE_URL,
  KEYCLOAK_ADMIN_CLIENT_ID,
  KEYCLOAK_ADMIN_CLIENT_SECRET,
} from '../const/constants';

export const MFA_CREDENTIAL_TYPES = ['otp', 'recovery-authn-codes'];

const getKeycloakAdminToken = async () => {
  if (!KEYCLOAK_ADMIN_CLIENT_SECRET || KEYCLOAK_ADMIN_CLIENT_SECRET === 'undefined') {
    throw new Error('KEYCLOAK_ADMIN_CLIENT_SECRET must be set to clean up MFA credentials.');
  }

  const response = await fetch(`${KEYCLOAK_ADMIN_BASE_URL}/realms/master/protocol/openid-connect/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: KEYCLOAK_ADMIN_CLIENT_ID,
      client_secret: KEYCLOAK_ADMIN_CLIENT_SECRET,
      grant_type: 'client_credentials',
    }),
  });
  const data = await response.json();

  if (!response.ok || !data.access_token) {
    throw new Error(`Could not get Keycloak admin token: ${JSON.stringify(data)}`);
  }

  return data.access_token as string;
};

export const fetchKeycloakCredentials = async () => {
  const adminToken = await getKeycloakAdminToken();
  const headers = { Authorization: `Bearer ${adminToken}`, Accept: 'application/json' };
  const usersResponse = await fetch(
    `${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users?${new URLSearchParams({
      username: ACCTS_OIDC_EMAIL,
      exact: 'true',
    })}`,
    { headers },
  );
  const users = await usersResponse.json();

  if (!usersResponse.ok || users.length !== 1) {
    throw new Error(`Could not load Keycloak user for cleanup: ${JSON.stringify(users)}`);
  }

  const credentialsResponse = await fetch(
    `${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users/${users[0].id}/credentials`,
    { headers },
  );
  const credentials = await credentialsResponse.json();

  if (!credentialsResponse.ok) {
    throw new Error(`Could not load Keycloak credentials: ${JSON.stringify(credentials)}`);
  }

  return { userId: users[0].id as string, credentials, headers };
};

export const removeExistingMfaCredentials = async () => {
  const { userId, credentials, headers } = await fetchKeycloakCredentials();

  for (const credential of credentials.filter((item: { type?: string }) =>
    MFA_CREDENTIAL_TYPES.includes(item.type ?? ''),
  )) {
    const deleteResponse = await fetch(
      `${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users/${userId}/credentials/${credential.id}`,
      { method: 'DELETE', headers },
    );
    if (!deleteResponse.ok) {
      throw new Error(`Could not delete Keycloak credential for cleanup: ${await deleteResponse.text()}`);
    }
  }
};

export const getUserSessionIds = async (): Promise<string[]> => {
  const { userId, headers } = await fetchKeycloakCredentials();
  const response = await fetch(`${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users/${userId}/sessions`, { headers });
  const sessions = await response.json();

  if (!response.ok) {
    throw new Error(`Could not load Keycloak sessions: ${JSON.stringify(sessions)}`);
  }

  return (sessions as Array<{ id: string }>).map((session) => session.id);
};

export const getRecoveryCodesCredentialMetadata = async () => {
  const { credentials } = await fetchKeycloakCredentials();
  return credentials
    .filter((item: { type?: string }) => item.type === 'recovery-authn-codes')
    .map((item: { id: string; createdDate?: number }) => ({ id: item.id, createdDate: item.createdDate }));
};
