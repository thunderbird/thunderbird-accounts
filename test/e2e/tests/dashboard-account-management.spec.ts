import {
  dashboardTest as test,
  skipDashboardTestsOnLocalDev,
} from '../utils/dashboard-test';
import {
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
} from '../const/constants';

test.describe('dashboard account management', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  skipDashboardTestsOnLocalDev();

  test('account management links navigate to the expected pages', async ({ dashboardPage }) => {
    // Mobile and desktop use their respective sign-in routes in the shared fixture.
    // Return to the dashboard between these internal account-management routes.
    await test.step('open the password change page', async () => {
      await dashboardPage.verifyPasswordChangeNavigation();
    });

    await dashboardPage.navigateToDashboard();

    await test.step('open the account deletion contact flow', async () => {
      await dashboardPage.verifyDeleteAccountNavigationOnly();
    });
  });
});
