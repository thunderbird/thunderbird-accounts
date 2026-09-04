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

test.describe('dashboard UI smoke test', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  skipDashboardTestsOnLocalDev();

  test('displays account details and provides working user menu controls', async ({ dashboardPage }) => {
    // The shared fixture follows the project-specific sign-in route: direct browser
    // sign-in on mobile, or reusable storage state with an auth check on desktop.
    await dashboardPage.verifyDashboardSignedIn();
    await dashboardPage.verifyDashboardDisplayed();
    await dashboardPage.verifyUserMenuControls();
  });
});
