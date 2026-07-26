import { test } from '@playwright/test';
import { DashboardPage } from '../../pages/dashboard-page';
import { ensureWeAreSignedIn } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_DEPLOYMENT_ANALYSIS,
  ACCTS_TARGET_ENV,
} from '../../const/constants';

let dashboardPage: DashboardPage;

test.beforeEach(async ({ page }) => {
  dashboardPage = new DashboardPage(page);
  await ensureWeAreSignedIn(page);
});

/**
 * Prerequisite: This test assumes that the test user (ACCTS_OIDC_EMAIL) already has a
 * Thundermail subscription and therefore after signing in, the main dashboard is visible
 * (and not redirected to the subscription page). If this test is running in CI on a new
 * local stack (i.e. on PRs) the test user (admin) won't yet have a subscription, therefore
 * skip this test when running in CI on PRs.
 */
test.describe('tb accounts sign-in is successful', {
  tag: [PLAYWRIGHT_TAG_DEPLOYMENT_ANALYSIS],
}, () => {
  test('accounts dashboard appears', async () => {
    // at this point regardless of env we will be signed in via the beforeEach
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate subscribe');
    await dashboardPage.navigateToDashboard();
    await dashboardPage.verifyDashboardSignedIn();
  });
});
