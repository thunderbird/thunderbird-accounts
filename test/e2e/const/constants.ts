// environment where the tests will run
export const ACCTS_TARGET_ENV = String(process.env.ACCTS_TARGET_ENV);

// tb accounts urls
export const ACCTS_CONTACT_URL = String(process.env.ACCTS_CONTACT_URL);

// sign-in credentials and corresponding account display name
export const ACCTS_OIDC_EMAIL = String(process.env.ACCTS_OIDC_EMAIL);
export const ACCTS_OIDC_PWORD = String(process.env.ACCTS_OIDC_PWORD);

// playwright test tags
export const PLAYWRIGHT_TAG_E2E_SUITE = '@e2e-suite';

// timeouts
export const TIMEOUT_2_SECONDS = 2000;
export const TIMEOUT_5_SECONDS = 5000;
export const TIMEOUT_30_SECONDS = 30000;
export const TIMEOUT_60_SECONDS = 60000;

// connection info
export const ACCTS_HOST = String(process.env.ACCTS_HOST);
export const IMAP_PORT = Number(process.env.IMAP_PORT);
export const JMAP_PORT = Number(process.env.JMAP_PORT);
export const SMTP_PORT = Number(process.env.SMTP_PORT);
export const IMAP_TLS = String(process.env.IMAP_TLS) ?? 'SSL/TLS';
export const JMAP_TLS = String(process.env.JMAP_TLS) ?? 'SSL/TLS';
export const SMTP_TLS = String(process.env.SMTP_TLS) ?? 'SSL/TLS';
export const APP_PASSWORD = 'Your App Password';
export const YOUR_EMAIL_LBL = 'Your email address:';
export const THUNDERMAIL_USERNAME = String(process.env.THUNDERMAIL_USERNAME);
export const THUNDERMAIL_EMAIL_ADDRESS = String(process.env.THUNDERMAIL_EMAIL_ADDRESS);

// mock responses
export const MOCK_RESPONSE_OK = {
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({
    fake_data: 'fake response data',
  }),
};
