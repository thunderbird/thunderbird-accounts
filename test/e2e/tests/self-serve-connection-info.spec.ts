import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';
import { navigateToAccountsSelfServeHubAndSignIn } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  CONNECTION_LOCALHOST,
  IMAP_SERVER_PORT,
  JMAP_SERVER_PORT,
  SMTP_SERVER_PORT,
  SECURITY_SSL_TLS,
  USERNAME_NONE,
  APP_PASSWORD_NONE,
 } from '../const/constants';

let selfServePage: SelfServePage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  fxaPage = new FxAPage(page);
  await navigateToAccountsSelfServeHubAndSignIn(page);
});

test.describe('tb accounts self-serve hub connection info', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('displayed correctly when no email is setup', async ({ page }) => {
    // headers and link
    await expect(selfServePage.selfServeHeader).toBeVisible();
    await expect(selfServePage.welcomeBackHeader).toBeVisible();
    await expect(selfServePage.accountInfoLink).toBeEnabled();

    // imap details
    expect(await selfServePage.imapServerName.innerText()).toBe(`Server Name: ${CONNECTION_LOCALHOST}`);
    expect(await selfServePage.imapServerPort.innerText()).toBe(`Server Port: ${IMAP_SERVER_PORT}`);
    expect(await selfServePage.imapSecurityType.innerText()).toBe(`Security: ${SECURITY_SSL_TLS}`);
    expect(await selfServePage.imapUsername.innerText()).toBe(`Username: ${USERNAME_NONE}`);
    expect(await selfServePage.imapPassword.innerText()).toBe(`Password: ${APP_PASSWORD_NONE}`);

    // jmap details
    expect(await selfServePage.jmapServerName.innerText()).toBe(`Server Name: ${CONNECTION_LOCALHOST}`);
    expect(await selfServePage.jmapServerPort.innerText()).toBe(`Server Port: ${JMAP_SERVER_PORT}`);
    expect(await selfServePage.jmapSecurityType.innerText()).toBe(`Security: ${SECURITY_SSL_TLS}`);
    expect(await selfServePage.jmapUsername.innerText()).toBe(`Username: ${USERNAME_NONE}`);
    expect(await selfServePage.jmapPassword.innerText()).toBe(`Password: ${APP_PASSWORD_NONE}`);

    // smtp details
    expect(await selfServePage.smtpServerName.innerText()).toBe(`Server Name: ${CONNECTION_LOCALHOST}`);
    expect(await selfServePage.smtpServerPort.innerText()).toBe(`Server Port: ${SMTP_SERVER_PORT}`);
    expect(await selfServePage.smtpSecurityType.innerText()).toBe(`Security: ${SECURITY_SSL_TLS}`);
    expect(await selfServePage.smtpUsername.innerText()).toBe(`Username: ${USERNAME_NONE}`);
    expect(await selfServePage.smtpPassword.innerText()).toBe(`Password: ${APP_PASSWORD_NONE}`)
  });
});
