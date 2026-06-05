// environment where the tests will run
export const ACCTS_TARGET_ENV = String(process.env.ACCTS_TARGET_ENV);

// tb accounts urls
export const ACCTS_HUB_URL = String(process.env.ACCTS_HUB_URL);
export const ACCTS_CONTACT_URL = String(`${ACCTS_HUB_URL}/contact`);
export const ACCTS_SIGN_UP_URL = String(`${ACCTS_HUB_URL}/sign-up`);
export const ACCTS_SUBSCRIBE_URL = String(`${ACCTS_HUB_URL}/subscribe`);
export const TB_PRO_WAIT_LIST_URL = String(process.env.TB_PRO_WAIT_LIST_URL);

// sign-in credentials and corresponding info
export const ACCTS_OIDC_EMAIL = String(process.env.ACCTS_OIDC_EMAIL);
export const ACCTS_OIDC_PWORD = String(process.env.ACCTS_OIDC_PWORD);
export const ACCTS_OIDC_RECOVERY_EMAIL = String(process.env.ACCTS_OIDC_RECOVERY_EMAIL);
export const PRIMARY_THUNDERMAIL_EMAIL = String(process.env.PRIMARY_THUNDERMAIL_EMAIL);

// expected dashboard subscription details
export const DASHBOARD_CURRENT_SUBSCRIPTION_PRICE = String(process.env.DASHBOARD_CURRENT_SUBSCRIPTION_PRICE);
export const DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE = String(process.env.DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE);
export const DASHBOARD_CURRENT_SUBSCRIPTION_SEND_STORAGE = String(process.env.DASHBOARD_CURRENT_SUBSCRIPTION_SEND_STORAGE);
export const DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES = String(process.env.DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES);
export const DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS = String(process.env.DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS);
export const MAIL_SUBSCRIPTION_ERROR_TEXT = 'Failed to load subscription information';

// playwright test tags
export const PLAYWRIGHT_TAG_E2E_SUITE = '@e2e-suite';
export const PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY = '@e2e-prod-desktop-nightly';
export const PLAYWRIGHT_TAG_E2E_SUITE_MOBILE = '@e2e-mobile-suite';
export const PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY = '@e2e-prod-mobile-nightly';

// timeouts
export const TIMEOUT_1_SECOND = 1000;
export const TIMEOUT_2_SECONDS = 2000;
export const TIMEOUT_5_SECONDS = 5000;
export const TIMEOUT_10_SECONDS = 5000;
export const TIMEOUT_30_SECONDS = 30000;

// connection info
export const ACCTS_HOST = String(process.env.ACCTS_HOST);
export const IMAP_PORT = Number(process.env.IMAP_PORT);
export const JMAP_PORT = Number(process.env.JMAP_PORT);
export const SMTP_PORT = Number(process.env.SMTP_PORT);
export const IMAP_TLS = String(process.env.IMAP_TLS) ?? 'SSL/TLS';
export const JMAP_TLS = String(process.env.JMAP_TLS) ?? 'SSL/TLS';
export const SMTP_TLS = String(process.env.SMTP_TLS) ?? 'SSL/TLS';
export const PADDLE_HOST = 'customer-portal.paddle.com';

export const DEFAULT_LOCALE = 'en';
export const DEFAULT_TIMEZONE = 'UTC';
