// environment where the tests will run
export const ACCTS_TARGET_ENV = String(process.env.ACCTS_TARGET_ENV);

// tb accounts urls
export const ACCTS_SELF_SERVE_URL = String(process.env.ACCTS_SELF_SERVE_URL);

// sign-in credentials and corresponding account display name
export const ACCTS_FXA_EMAIL = String(process.env.ACCTS_FXA_EMAIL);
export const ACCTS_FXA_PWORD = String(process.env.ACCTS_FXA_PWORD);

// playwright test tags
export const PLAYWRIGHT_TAG_E2E_SUITE = '@e2e-suite';

// timeouts
export const TIMEOUT_2_SECONDS = 2000;
