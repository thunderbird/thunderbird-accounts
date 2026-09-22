import { test } from '@playwright/test';
import { EmailSettingsPage } from '../../pages/email-settings-page';
import { navigateToAccountsHubAndSignIn } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../../const/constants';

let emailSettingsPage: EmailSettingsPage;

test.beforeEach(async ({ page }) => {
  emailSettingsPage = new EmailSettingsPage(page);
  await navigateToAccountsHubAndSignIn(page);
});

test.describe('email settings page components on mobile browser', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE_MOBILE, PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY],
}, () => {
  test('all visible email settings page components work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate subscribe step');

    await emailSettingsPage.navigateToEmailSettings();
    await emailSettingsPage.verifyEmailSettingsComponents();
    await emailSettingsPage.verifyCustomDomainsComponents();
  });
});
