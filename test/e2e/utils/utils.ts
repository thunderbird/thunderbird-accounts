// utility functions that may be used by any tests
import { TBAcctsOIDCPage } from "../pages/tb-accts-oidc-page";
import { TBAcctsHubPage } from "../pages/tb-accts-hub-page";
import { expect, type Locator, type Page, Browser, request } from '@playwright/test';
import path from 'path';

import {
    ACCTS_TARGET_ENV,
    ACCTS_HUB_URL,
    TIMEOUT_30_SECONDS,
    TIMEOUT_60_SECONDS,
} from "../const/constants";

export const authFile = path.join(__dirname, '../test-results/.auth/user.json');

export const isAllowListEnabled = async (page: Page) => {
    return await page.evaluate('window?._page?.features?.be_allowList');
};

/**
 * Allows you to show the current page's console log in stdout
 */
export const showPageConsoleLog = async (page: Page) => {
    // Listen for all console logs
    page.on('console', msg => console.log(`> ${msg.text()}`));

}

/**
 * Override values on the server-rendered window._page object before the Vue app reads it.
 */
export const overridePageData = async (page: Page, overrides: Record<string, unknown>) => {
    await page.addInitScript((pageOverrides) => {
        let pageData: Record<string, unknown>;

        Object.defineProperty(window, '_page', {
            configurable: true,
            get() {
                return pageData;
            },
            set(value: Record<string, unknown>) {
                pageData = { ...value, ...pageOverrides };
            },
        });
    }, overrides);
};
  
/**
 * Similar to waitForLoadState but works with our vue applications.
 * During App.vue's onMounted (aka the ready state for our vue app) we add a testid to body, 
 * this will await domcontentloaded and then look for that testid. 
 */
export const waitForVueApp = async (page: Page) => {
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('[data-testid=vue-app]');
}

type AuthenticationState = 'loading' | 'sign-in-ready' | 'terms-of-service' | 'signed-in';

type AuthenticationSnapshot = {
    state: AuthenticationState;
    isSignedIn: boolean;
    isTermsOfServiceVisible: boolean;
    isSignInHeaderVisible: boolean;
    isEmailInputVisible: boolean;
    isPasswordInputVisible: boolean;
    isSignInButtonVisible: boolean;
    isSignInButtonEnabled: boolean;
};

const getAuthenticationSnapshot = async (
    tbAcctsSignInPage: TBAcctsOIDCPage,
    tbAcctsHubPage: TBAcctsHubPage,
): Promise<AuthenticationSnapshot> => {
    const [
        isSignedIn,
        isTermsOfServiceVisible,
        isSignInHeaderVisible,
        isEmailInputVisible,
        isPasswordInputVisible,
        isSignInButtonVisible,
        isSignInButtonEnabled,
    ] = await Promise.all([
        tbAcctsHubPage.userAvatar.isVisible().catch(() => false),
        tbAcctsHubPage.acceptTOSButton.isVisible().catch(() => false),
        tbAcctsSignInPage.signInHeaderText.isVisible().catch(() => false),
        tbAcctsSignInPage.emailInput.isVisible().catch(() => false),
        tbAcctsSignInPage.passwordInput.isVisible().catch(() => false),
        tbAcctsSignInPage.signInButton.isVisible().catch(() => false),
        tbAcctsSignInPage.signInButton.isEnabled().catch(() => false),
    ]);

    let state: AuthenticationState = 'loading';
    if (isSignedIn) {
        state = 'signed-in';
    } else if (isTermsOfServiceVisible) {
        state = 'terms-of-service';
    } else if (
        isSignInHeaderVisible
        && isEmailInputVisible
        && isPasswordInputVisible
        && isSignInButtonVisible
        && isSignInButtonEnabled
    ) {
        state = 'sign-in-ready';
    }

    return {
        state,
        isSignedIn,
        isTermsOfServiceVisible,
        isSignInHeaderVisible,
        isEmailInputVisible,
        isPasswordInputVisible,
        isSignInButtonVisible,
        isSignInButtonEnabled,
    };
};

const sanitizeUrlForDiagnostics = (url: string) => {
    try {
        const sanitizedUrl = new URL(url);
        sanitizedUrl.search = '';
        sanitizedUrl.hash = '';
        return sanitizedUrl.toString();
    } catch {
        return url.split(/[?#]/, 1)[0];
    }
};

const waitForBrowserStackAndroidAuthenticationState = async (
    tbAcctsSignInPage: TBAcctsOIDCPage,
    tbAcctsHubPage: TBAcctsHubPage,
    expectedStates: AuthenticationState[],
    message: string,
) => {
    const stateLocators: Array<{ state: AuthenticationState; locator: Locator }> = [];
    if (expectedStates.includes('signed-in')) {
        stateLocators.push({ state: 'signed-in', locator: tbAcctsHubPage.userAvatar });
    }
    if (expectedStates.includes('terms-of-service')) {
        stateLocators.push({ state: 'terms-of-service', locator: tbAcctsHubPage.acceptTOSButton });
    }
    if (expectedStates.includes('sign-in-ready')) {
        // Detailed field and button readiness is checked by TBAcctsOIDCPage.signIn().
        stateLocators.push({ state: 'sign-in-ready', locator: tbAcctsSignInPage.signInHeaderText });
    }

    expect(stateLocators, 'expected at least one authentication state locator').not.toHaveLength(0);
    const combinedStateLocator = stateLocators
        .slice(1)
        .reduce(
            (combinedLocator, stateLocator) => combinedLocator.or(stateLocator.locator),
            stateLocators[0].locator,
        );
    const deadline = Date.now() + TIMEOUT_60_SECONDS;

    while (Date.now() < deadline) {
        await expect(combinedStateLocator, message).toBeVisible({
            timeout: Math.max(1, deadline - Date.now()),
        });

        // The combined locator performs the retrying remote wait once. These
        // one-time checks only identify which of the expected states appeared.
        for (const stateLocator of stateLocators) {
            if (await stateLocator.locator.isVisible().catch(() => false)) {
                return stateLocator.state;
            }
        }
        // Navigation may replace the winning element between the combined wait
        // and identification. In that narrow case, wait on the combined signal again.
    }

    return 'loading';
};

const waitForAuthenticationState = async (
    page: Page,
    tbAcctsSignInPage: TBAcctsOIDCPage,
    tbAcctsHubPage: TBAcctsHubPage,
    expectedStates: AuthenticationState[],
    message: string,
    isBrowserStackAndroid: boolean = false,
) => {
    const authenticationResult: { state: AuthenticationState } = { state: 'loading' };

    try {
        if (isBrowserStackAndroid) {
            authenticationResult.state = await waitForBrowserStackAndroidAuthenticationState(
                tbAcctsSignInPage,
                tbAcctsHubPage,
                expectedStates,
                message,
            );
            expect(authenticationResult.state, message).toMatch(
                new RegExp(`^(${expectedStates.join('|')})$`),
            );
        } else {
            // Keep the established desktop and emulated-device polling behavior.
            await expect.poll(
                async () => {
                    const snapshot = await getAuthenticationSnapshot(tbAcctsSignInPage, tbAcctsHubPage);
                    authenticationResult.state = snapshot.state;
                    return authenticationResult.state;
                },
                { timeout: TIMEOUT_60_SECONDS, message },
            ).toMatch(new RegExp(`^(${expectedStates.join('|')})$`));
        }
    } catch (error) {
        const [pageTitle, finalSnapshot] = await Promise.all([
            page.title().catch(() => '<unavailable>'),
            getAuthenticationSnapshot(tbAcctsSignInPage, tbAcctsHubPage).catch(() => null),
        ]);

        // The expected UI can appear between expect.poll's final sample and
        // this diagnostic snapshot, especially on slower BrowserStack devices.
        if (finalSnapshot && expectedStates.includes(finalSnapshot.state)) {
            return finalSnapshot.state;
        }

        const stateSummary = finalSnapshot
            ? `state='${finalSnapshot.state}', avatar=${finalSnapshot.isSignedIn}, `
                + `terms=${finalSnapshot.isTermsOfServiceVisible}, `
                + `sign-in header=${finalSnapshot.isSignInHeaderVisible}, `
                + `email input=${finalSnapshot.isEmailInputVisible}, `
                + `password input=${finalSnapshot.isPasswordInputVisible}, `
                + `button visible=${finalSnapshot.isSignInButtonVisible}, `
                + `button enabled=${finalSnapshot.isSignInButtonEnabled}`
            : 'state unavailable';
        throw new Error(
            `Authentication did not settle in one of the expected states (${expectedStates.join(', ')}). `
            + `Final URL: ${sanitizeUrlForDiagnostics(page.url())}. `
            + `Page title: '${pageTitle}'. Final authentication UI: ${stateSummary}.`,
            { cause: error },
        );
    }

    return authenticationResult.state;
};

type SignInOptions = {
    username?: string | null;
    password?: string | null;
    isMobileAndroid?: boolean;
    isBrowserStackAndroid?: boolean;
};

/**
 * Navigate to TB Accounts Hub (at the ACCTS_HUB_URL in the test/e2e/.env file). If already signed
 * in then just exit; otherwise if not currently signed in then sign in using the credentials
 * provided in the .env file. When signing in to the local stack we use a local sign in page and
 * aren't redirected to TB Accounts OIDC to sign in.
 * 
 * If username or password aren't provided the env values will be used. Set
 * Android project flags select the platform-specific submission workaround.
 */
export const navigateToAccountsHubAndSignIn = async (
    page: Page,
    {
        username = null,
        password = null,
        isMobileAndroid = false,
        isBrowserStackAndroid = false,
    }: SignInOptions = {},
) => {
    console.log(`navigating to accounts hub ${ACCTS_TARGET_ENV} (${ACCTS_HUB_URL})`);   
    const tbAcctsSignInPage = new TBAcctsOIDCPage(
        page,
        isMobileAndroid,
        isBrowserStackAndroid,
    );
    const tbAcctsHubPage = new TBAcctsHubPage(page);
    
    await page.goto(`${ACCTS_HUB_URL}`, {
        waitUntil: 'domcontentloaded',
        timeout: TIMEOUT_60_SECONDS,
    });
    await waitForVueApp(page);

    // Wait for a complete state instead of taking a point-in-time visibility
    // snapshot while Accounts or Keycloak may still be rendering or redirecting.
    let authenticationState = await waitForAuthenticationState(
        page,
        tbAcctsSignInPage,
        tbAcctsHubPage,
        ['signed-in', 'terms-of-service', 'sign-in-ready'],
        'waiting for the initial authentication state',
        isBrowserStackAndroid,
    );

    if (authenticationState === 'sign-in-ready') {
        await tbAcctsSignInPage.signIn(username, password);
        authenticationState = await waitForAuthenticationState(
            page,
            tbAcctsSignInPage,
            tbAcctsHubPage,
            ['signed-in', 'terms-of-service'],
            'waiting for sign-in to complete',
            isBrowserStackAndroid,
        );
    }

    // New local stacks or accounts can require policy acceptance before the
    // normal signed-in hub is available.
    if (authenticationState === 'terms-of-service') {
        console.log('accepting the TB Pro ToS');
        await expect(tbAcctsHubPage.acceptTOSButton).toBeEnabled({ timeout: TIMEOUT_30_SECONDS });
        await tbAcctsHubPage.acceptTOSButton.click({ timeout: TIMEOUT_30_SECONDS });
        await waitForAuthenticationState(
            page,
            tbAcctsSignInPage,
            tbAcctsHubPage,
            ['signed-in'],
            'waiting for the signed-in hub after accepting the terms of service',
            isBrowserStackAndroid,
        );
    }

    // The banner avatar is the stable signed-in signal after the nav overhaul in #695.
    await expect(tbAcctsHubPage.userAvatar).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
}

/**
 * Ensure we are already signed into TB Accounts, and if we aren't then sign in. Also set
 * save the storage and auth state. This is meant to be used at the start of each test to ensure
 * we are signed in; the auth.desktop.setup already signs us in before all of the tests begin
 * however if the tests go long the TB Accounts login session can expire.
 */
export const ensureWeAreSignedIn = async (page: Page) => {
    await navigateToAccountsHubAndSignIn(page);
    await page.context().storageState({ path: authFile });
}
