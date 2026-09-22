import { test } from '@playwright/test';
import { EmailSettingsPage } from '../../pages/email-settings-page';
import { ensureWeAreSignedIn } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../../const/constants';

let emailSettingsPage: EmailSettingsPage;

test.beforeEach(async ({ page }) => {
  emailSettingsPage = new EmailSettingsPage(page);
  await ensureWeAreSignedIn(page);
});

test.describe('email settings page components on desktop browser', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE, PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY],
}, () => {
  test('all visible email settings page components work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate subscribe step');
    await emailSettingsPage.navigateToEmailSettings();
    await emailSettingsPage.verifyEmailSettingsComponents();
    await emailSettingsPage.verifyCustomDomainsComponents();
  });
});
