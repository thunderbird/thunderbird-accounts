// environment where the tests will run
export const ACCTS_TARGET_ENV = String(process.env.ACCTS_TARGET_ENV);

// tb accounts urls
export const ACCTS_SELF_SERVE_URL = String(process.env.ACCTS_SELF_SERVE_URL);
export const ACCTS_SELF_SERVE_ACCT_INFO_URL = `${ACCTS_SELF_SERVE_URL}account-settings`;
export const ACCTS_EMAIL_SIGN_UP_URL = String(process.env.ACCTS_EMAIL_SIGN_UP_URL);

// sign-in credentials and corresponding account display name
export const ACCTS_FXA_EMAIL = String(process.env.ACCTS_FXA_EMAIL);
export const ACCTS_FXA_PWORD = String(process.env.ACCTS_FXA_PWORD);

// playwright test tags
export const PLAYWRIGHT_TAG_E2E_SUITE = '@e2e-suite';

// timeouts
export const TIMEOUT_2_SECONDS = 2000;

// connection info
export const IMAP_SERVER_HOST = String(process.env.IMAP_HOST || 'localhost');
export const IMAP_SERVER_PORT = Number(process.env.IMAP_PORT || 993);
export const JMAP_SERVER_HOST = String(process.env.JMAP_HOST || 'localhost');
export const JMAP_SERVER_PORT = Number(process.env.JMAP_PORT || 7768);
export const SMTP_SERVER_HOST = String(process.env.SMTP_HOST || 'localhost');
export const SMTP_SERVER_PORT = Number(process.env.SMTP_PORT || 7768);
export const SECURITY_SSL_TLS = 'SSL/TLS';
export const USERNAME_NONE = 'None';
export const APP_PASSWORD_NONE = 'Your App Password';

// email sign-up
export const EMAIL_SIGN_UP_EMAIL_ADDRESS = 'my-new-email-address';
export const EMAIL_SIGN_UP_DOMAIN = 'tb.pro';
export const EMAIL_SIGN_UP_APP_PWORD = 'password';

// mock responses
export const MOCK_RESPONSE_OK = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
      fake_data: 'fake response data',
  })
};
