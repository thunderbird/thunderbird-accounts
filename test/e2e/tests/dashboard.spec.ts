import { test } from '@playwright/test';
import { DashboardPage } from '../pages/dashboard-page';
import { isMobileAndroidProject, navigateToAccountsHubAndSignIn } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../const/constants';

let dashboardPage: DashboardPage;

test.beforeEach(async ({ page }, testInfo) => {
  const isMobileAndroid = isMobileAndroidProject(testInfo.project.name);
  dashboardPage = new DashboardPage(page, isMobileAndroid);
  await navigateToAccountsHubAndSignIn(page, {
    isMobileAndroid,
  });
});

/**
 * Prerequisite: This test assumes that the signed-in user already has a TB Pro subscription
 * and therefore the main dashboard is visible (and not redirected to the subscription page).
 * On a new local dev stack (including PR CI), the test user does not yet have a subscription,
 * so this scenario is skipped. The existing stage and prod nightly accounts are subscribed.
 * Issue 771 tracks adding a subscribe step so this can run on new local stacks too.
 */
test.describe('dashboard controls on browser', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  test('all visible dashboard controls work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate tb subscribe step');

    await dashboardPage.navigateToDashboard();
    await dashboardPage.verifyDashboardSignedIn();
    await dashboardPage.verifyDashboardDisplayed();
    await dashboardPage.verifyGetStartedComponents();

    await dashboardPage.verifyPasswordChangeNavigation();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyDeleteAccountNavigationOnly();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyServiceAppsLoadAfterNavigation();
    await dashboardPage.verifyManageSubscriptionOpensPortal();
    await dashboardPage.verifyUserMenuControls();
  });

  test.describe('app passwords', () => {
    let appPasswordToCleanUp: string | undefined;

    test.afterEach(async () => {
      const name = appPasswordToCleanUp;
      appPasswordToCleanUp = undefined;
      if (name) {
        await dashboardPage.removeAppPasswordIfPresent(name);
      }
    });

    test('creates, copies, and removes an app password', async () => {
      // Accounts supports multiple app passwords; test creating a new one and then removing it, but leave any
      // existing app passwords alone as we don't want the tests deleting anyone's app password that they might be using
      test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate tb subscribe step');

      await dashboardPage.navigateToDashboard();
      const name = `E2E-${new Date().toISOString()}-${crypto.randomUUID().slice(0, 8)}`;
      appPasswordToCleanUp = name;

      await dashboardPage.createAppPassword(name);
      await dashboardPage.removeAppPassword(name);
      appPasswordToCleanUp = undefined;
    });
  });
});
