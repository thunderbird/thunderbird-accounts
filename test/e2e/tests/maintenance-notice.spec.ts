import { test, expect, type Page } from '@playwright/test';
import { TBAcctsOIDCPage } from '../pages/tb-accts-oidc-page';
import { waitForVueApp } from '../utils/utils';
import { deleteRealmMessage, setRealmMessage } from '../utils/keycloak-admin';

import {
  ACCTS_HUB_URL,
  ACCTS_TARGET_ENV,
  KEYCLOAK_ADMIN_CLIENT_SECRET,
  PLAYWRIGHT_TAG_E2E_SUITE,
  TIMEOUT_30_SECONDS,
  TIMEOUT_60_SECONDS,
} from '../const/constants';

const NOTICE_MESSAGE = 'Scheduled maintenance 14:00–16:00 UTC.';
const STATUS_URL = 'https://status.example.org/';

const openLoginPage = async (page: Page) => {
  await page.goto(ACCTS_HUB_URL, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_60_SECONDS });
  await waitForVueApp(page);

  const signInPage = new TBAcctsOIDCPage(page);
  await expect(signInPage.signInHeaderText).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
  return signInPage;
};

test.describe(
  'maintenance notice',
  {
    tag: [PLAYWRIGHT_TAG_E2E_SUITE],
  },
  () => {
    // The notice is a tbpro realm override, which every visitor of that Keycloak sees.
    test.skip(ACCTS_TARGET_ENV !== 'dev', 'Only runs against the local stack.');
    test.skip(
      !KEYCLOAK_ADMIN_CLIENT_SECRET || KEYCLOAK_ADMIN_CLIENT_SECRET === 'undefined',
      'KEYCLOAK_ADMIN_CLIENT_SECRET is needed for this test to run.'
    );

    // Start signed out so the hub redirects to the Keycloak login page.
    test.use({ storageState: { cookies: [], origins: [] } });

    test.afterEach(async () => {
      for (const key of ['maintenanceNotice', 'maintenanceNoticeType', 'maintenanceNoticeStatusUrl']) {
        await deleteRealmMessage(key);
      }
    });

    test('shows the maintenanceNotice realm message with a status link above the invite-only notice', async ({
      page,
    }) => {
      await setRealmMessage('maintenanceNotice', NOTICE_MESSAGE);
      await setRealmMessage('maintenanceNoticeType', 'critical');
      await setRealmMessage('maintenanceNoticeStatusUrl', STATUS_URL);

      const signInPage = await openLoginPage(page);

      const notice = page.getByTestId('maintenance-notice');
      await expect(notice).toContainText(NOTICE_MESSAGE);
      await expect(notice).toHaveClass(/critical/);
      await expect(page.getByTestId('maintenance-notice-status-url')).toHaveText('Status');
      await expect(page.getByTestId('maintenance-notice-status-url')).toHaveAttribute('href', STATUS_URL);
      await expect(page.getByTestId('go-to-invite-only-url')).toBeVisible();
      await expect(signInPage.emailInput).toBeEditable();
    });

    test('does not link a status URL that is not http(s)', async ({ page }) => {
      await setRealmMessage('maintenanceNotice', NOTICE_MESSAGE);
      await setRealmMessage('maintenanceNoticeStatusUrl', 'javascript:alert(1)');

      await openLoginPage(page);

      await expect(page.getByTestId('maintenance-notice')).toContainText(NOTICE_MESSAGE);
      await expect(page.getByTestId('maintenance-notice-status-url')).toHaveCount(0);
    });

    test('shows no notice when maintenanceNotice is not overridden', async ({ page }) => {
      const signInPage = await openLoginPage(page);

      await expect(signInPage.emailInput).toBeVisible();
      await expect(page.getByTestId('maintenance-notice')).toHaveCount(0);
      await expect(page.getByTestId('go-to-invite-only-url')).toBeVisible();
    });
  }
);
