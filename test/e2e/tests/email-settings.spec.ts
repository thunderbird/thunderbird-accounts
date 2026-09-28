import { test } from '@playwright/test';
import { EmailSettingsPage } from '../pages/email-settings-page';
import { isMobileAndroidProject, ensureWeAreSignedIn, navigateToAccountsHubAndSignIn } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../const/constants';

let emailSettingsPage: EmailSettingsPage;

test.beforeEach(async ({ page }, testInfo) => {
  emailSettingsPage = new EmailSettingsPage(page);

  if (isMobileAndroidProject(testInfo.project.name)) {
    // Android projects cannot load the saved desktop context, so each test signs in separately.
    await navigateToAccountsHubAndSignIn(page, {
      isMobileAndroid: true,
    });
  } else {
    // Desktop projects load auth.desktop.setup.ts's context; refresh it if the session expired.
    await ensureWeAreSignedIn(page);
  }
});

test.describe('email settings page components on browser', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  test('all visible email settings page components work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate subscribe step');

    await emailSettingsPage.navigateToEmailSettings();
    await emailSettingsPage.verifyEmailSettingsComponents();
    await emailSettingsPage.verifyCustomDomainsComponents();
  });
});
