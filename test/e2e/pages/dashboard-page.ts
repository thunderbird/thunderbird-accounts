import { expect, type Locator, type Page } from '@playwright/test';
import {
  ACCTS_HOST,
  ACCTS_HUB_URL,
  ACCTS_OIDC_EMAIL,
  DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS,
  DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES,
  DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE,
  DASHBOARD_CURRENT_SUBSCRIPTION_PRICE,
  DASHBOARD_CURRENT_SUBSCRIPTION_SEND_STORAGE,
  IMAP_PORT,
  IMAP_TLS,
  JMAP_PORT,
  JMAP_TLS,
  PADDLE_HOST,
  SMTP_PORT,
  SMTP_TLS,
  TIMEOUT_2_SECONDS,
  TIMEOUT_5_SECONDS,
  TIMEOUT_30_SECONDS,
  TIMEOUT_60_SECONDS,
} from '../const/constants';
import { waitForVueApp } from '../utils/utils';

interface ServiceUrls {
  mail: string;
  appointment: string;
  send: string;
}

type PopupPageAssertion = {
  link: Locator;
  expectedUrl: string;
  expectedElementName?: string;
  expectedElement?: (page: Page) => Locator;
  beforeExpectedElements?: Array<{
    expectedElementName: string;
    expectedElement: (page: Page) => Locator;
  }>;
};

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const hasTls = (tls: string) => Boolean(tls && tls !== 'None' && tls !== 'undefined');
const formatPort = (port: number, tls: string) => `${port}${hasTls(tls) ? ' (SSL/TLS)' : ''}`;

export class DashboardPage {
  readonly page: Page;
  readonly myAccountHeading: Locator;
  readonly myAccountCard: Locator;
  readonly displayNameSection: Locator;
  readonly appPasswordSection: Locator;
  readonly accountDeletionHeading: Locator;
  readonly thunderbirdAppsHeading: Locator;
  readonly currentSubscriptionHeading: Locator;
  readonly currentSubscriptionSection: Locator;
  readonly getStartedHeading: Locator;
  readonly getStartedSection: Locator;
  readonly passwordChangeLink: Locator;
  readonly updatePasswordHeader: Locator;
  readonly deleteAccountLink: Locator;
  readonly thundermailLink: Locator;
  readonly appointmentLink: Locator;
  readonly sendLink: Locator;
  readonly manageSubscriptionButton: Locator;
  readonly userAvatar: Locator;
  readonly supportLink: Locator;
  readonly logoutLink: Locator;
  readonly contactHeader: Locator;

  constructor(page: Page) {
    this.page = page;
    this.myAccountHeading = this.page.getByRole('heading', { name: 'Account settings' });
    this.myAccountCard = this.page.locator('.my-account-card');
    this.displayNameSection = this.myAccountCard.locator('.display-name-container');
    this.appPasswordSection = this.myAccountCard.locator('#app-password-container');
    this.accountDeletionHeading = this.page.getByRole('heading', { name: 'Account Deletion' });
    this.thunderbirdAppsHeading = this.page.getByRole('heading', { name: 'Thunderbird Apps' });
    this.currentSubscriptionHeading = this.page.getByRole('heading', { name: 'Current Subscription' });
    this.currentSubscriptionSection = this.page.locator('section').filter({ has: this.currentSubscriptionHeading });
    this.getStartedHeading = this.page.getByRole('heading', { name: 'Get started with Thundermail' });
    this.getStartedSection = this.page.locator('section').filter({ has: this.getStartedHeading });
    this.passwordChangeLink = this.page.locator('a[href="/reset-password/"]');
    this.updatePasswordHeader = this.page.getByRole('heading', { name: 'Update password' });
    this.deleteAccountLink = this.page.getByRole('link', { name: 'Contact support' });
    this.thundermailLink = this.page.locator('.service-icon-link').filter({ hasText: 'Mail' });
    this.appointmentLink = this.page.locator('.service-icon-link').filter({ hasText: 'Appointment' });
    this.sendLink = this.page.locator('.service-icon-link').filter({ hasText: 'Send' });
    this.manageSubscriptionButton = this.page.getByRole('button', { name: 'Manage Subscription' });
    this.userAvatar = this.page.getByRole('banner').locator('.avatar');

    // Scope menu links to the user menu dropdown
    const userMenuDropdown = this.page.getByRole('banner').locator('.user-menu .dropdown');
    this.supportLink = userMenuDropdown.getByRole('link', { name: 'Support', exact: true });
    this.logoutLink = userMenuDropdown.getByRole('link', { name: 'Logout', exact: true });
    this.contactHeader = this.page.getByRole('heading', { name: 'Submit a request' });
  }

  async navigateToDashboard() {
    await this.page.goto(`${ACCTS_HUB_URL}/dashboard`);
    await this.waitForPageToSettle();
    // This test expects that the signed-in user already has a tb pro subscription setup
    // so the dashboard is displayed after sign-in and not the tb pro subscription page
    await expect.poll(async () => new URL(this.page.url()).pathname).toBe('/dashboard');
  }

  async verifyDashboardSignedIn() {
    // just verify we are signed in and header appears
    await expect(this.myAccountHeading).toBeVisible( { timeout: TIMEOUT_30_SECONDS });
    await expect(this.accountDeletionHeading).toBeVisible();
    await expect(this.thunderbirdAppsHeading).toBeVisible();
  }

  async verifyDashboardDisplayed() {
    await expect(this.myAccountCard).toContainText(ACCTS_OIDC_EMAIL);
    await expect(this.currentSubscriptionHeading).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.currentSubscriptionSection).toContainText(DASHBOARD_CURRENT_SUBSCRIPTION_PRICE);
    await expect(this.currentSubscriptionSection).toContainText(
      new RegExp(`${escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE)}\\s*of Mail Storage`),
    );
    await expect(this.currentSubscriptionSection).toContainText(
      new RegExp(`${escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_SEND_STORAGE)}\\s*of Send Storage`),
    );
    await expect(this.currentSubscriptionSection).toContainText(
      new RegExp(`${escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES)}\\s*Email Addresses`),
    );
    await expect(this.currentSubscriptionSection).toContainText(
      new RegExp(`${escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS)}\\s*Custom Domains`),
    );
    await expect(this.passwordChangeLink).toBeVisible();
    await expect(this.deleteAccountLink).toBeVisible();
    await expect(this.thundermailLink).toBeVisible();
    await expect(this.appointmentLink).toBeVisible();
    await expect(this.sendLink).toBeVisible();
    await expect(this.manageSubscriptionButton).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

    await this.verifyDisplayNameFormOpensAndCancels();
    await this.verifyAppPasswordFormOpensAndCancels();
}

  async verifyGetStartedComponents() {
    await this.getStartedSection.scrollIntoViewIfNeeded();
    await expect(this.getStartedHeading).toBeVisible();
    await expect(this.getStartedSection).toContainText('Connect your new email address to start sending and receiving.');

    await this.verifyPinToggle();
    await this.verifyDesktopSetupTab();
    await this.verifyMobileSetupTab();
    await this.verifyOtherAppsSetupTab();
  }

  async verifyPasswordChangeNavigation() {
    await this.passwordChangeLink.click({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.updatePasswordHeader).toBeVisible({ timeout: TIMEOUT_60_SECONDS });
  }

  async verifyDeleteAccountNavigationOnly() {
    await this.deleteAccountLink.click();
    await this.verifyContactScreenDisplayed();
  }

  async verifyServiceAppsLoadAfterNavigation() {
    const serviceUrls = await this.getConfiguredServiceUrls();
    // Mail, Appointment and Send are all configured external services that open in popups.
    await this.verifyPopupServiceAppLoads({
      link: this.thundermailLink,
      expectedUrl: serviceUrls.mail,
    });
    await this.verifyPopupServiceAppLoads({
      link: this.appointmentLink,
      expectedUrl: serviceUrls.appointment,
      beforeExpectedElements: [{
        expectedElementName: 'Need help? Visit support',
        expectedElement: page => page.locator('footer').getByRole('link', { name: /visit support/i }),
      }],
      expectedElementName: 'Copy booking link',
      expectedElement: page => page.getByRole('button', { name: /copy booking link/i }),
    });
    await this.verifyPopupServiceAppLoads({
      link: this.sendLink,
      expectedUrl: serviceUrls.send,
      beforeExpectedElements: [{
        expectedElementName: 'Need help? Visit support',
        expectedElement: page => page.locator('footer').getByRole('link', { name: /visit support/i }),
      }],
      expectedElementName: 'Recover access',
      expectedElement: page => page.getByTestId('recover-access-button'),
    });
  }

  async verifyManageSubscriptionOpensPortal() {
    const [popup] = await Promise.all([
      this.page.waitForEvent('popup'),
      this.manageSubscriptionButton.click(),
    ]);

    await expect.poll(async () => popup.url()).not.toBe('about:blank');
    expect(new URL(popup.url()).protocol).toMatch(/^https?:$/);
    expect(new URL(popup.url()).host).toContain(PADDLE_HOST);
    await popup.close();
  }

  async verifyUserMenuControls() {
    await this.userAvatar.click();
    await expect(this.supportLink).toBeVisible();
    await expect(this.logoutLink).toBeVisible();
    await expect(this.logoutLink).toHaveAttribute('href', '/logout/');

    await this.supportLink.click();
    await this.verifyContactScreenDisplayed();
  }

  private async verifyDisplayNameFormOpensAndCancels() {
    await expect(this.displayNameSection).toContainText('Display name');
    await this.displayNameSection.getByRole('button', { name: 'Change' }).click();
    await expect(this.displayNameSection.getByTestId('display-name-input')).toBeVisible();
    await expect(this.displayNameSection.getByRole('button', { name: 'Save' })).toBeVisible();
    await this.displayNameSection.getByRole('button', { name: 'Cancel' }).click();
    await expect(this.displayNameSection.getByTestId('display-name-input')).not.toBeVisible();
  }

  private async verifyAppPasswordFormOpensAndCancels() {
    await expect(this.appPasswordSection).toContainText('App Password');
    await expect(this.appPasswordSection).toContainText(/Set|Not set/);
    await this.appPasswordSection.getByRole('button', { name: /^(Create|Change) app password$/ }).click();
    await expect(this.appPasswordSection.getByTestId('app-passwords-add-password-input')).toBeVisible();
    await expect(this.appPasswordSection.getByTestId('app-passwords-add-password-confirm-input')).toBeVisible();
    await expect(this.appPasswordSection.getByRole('button', { name: 'Save' })).toBeVisible();
    await this.appPasswordSection.getByRole('button', { name: 'Cancel' }).click();
    await expect(this.appPasswordSection.getByTestId('app-passwords-add-password-input')).not.toBeVisible();
  }

  private async verifyPinToggle() {
    const unpinButton = this.getStartedSection.getByRole('button', { name: 'Unpin' });
    await expect(unpinButton).toBeVisible();
    await unpinButton.click();
    await expect(this.getStartedSection.getByRole('button', { name: 'Pin' })).toBeVisible();
    await this.getStartedSection.getByRole('button', { name: 'Pin' }).click();
    await expect(unpinButton).toBeVisible();
  }

  private async verifyDesktopSetupTab() {
    await this.getStartedSection.getByRole('tab', { name: 'Desktop' }).click();
    await expect(this.getStartedSection.getByRole('tab', { name: 'Desktop' })).toHaveAttribute('aria-selected', 'true');
    await expect(this.getStartedSection).toContainText(/Automatic Configuration|Connect Thunderbird Desktop/);
    await expect(this.getStartedSection).toContainText('Download Thunderbird Desktop');

    const downloadLink = this.getStartedSection.getByRole('link', { name: 'Download' });
    await expect(downloadLink).toBeVisible();
    await expect(downloadLink).toHaveAttribute('href', /thunderbird\.net\/thunderbird\/all/);
    await expect(downloadLink).toHaveAttribute('target', '_blank');
  }

  private async verifyMobileSetupTab() {
    await this.getStartedSection.getByRole('tab', { name: 'Mobile' }).click();
    await expect(this.getStartedSection.getByRole('tab', { name: 'Mobile' })).toHaveAttribute('aria-selected', 'true');
    await expect(this.getStartedSection).toContainText('Scan QR Code');
    await expect(this.getStartedSection).toContainText('Download Thunderbird for Android');
    await expect(this.getStartedSection).toContainText('Need iOS Help?');

    const scanQrCodeButton = this.getStartedSection.getByRole('button', { name: 'Scan QR Code' });
    await expect(scanQrCodeButton).toBeVisible();
    await scanQrCodeButton.click();
    await expect(this.getStartedSection.getByRole('img', { name: /QR Code/i })).toBeVisible();

    const downloadLink = this.getStartedSection.getByRole('link', { name: 'Download' });
    await expect(downloadLink).toHaveAttribute('href', /play\.google\.com\/store\/apps\/details/);
    await expect(downloadLink).toHaveAttribute('target', '_blank');

    const supportLink = this.getStartedSection.getByRole('link', { name: 'Visit Support Article' });
    await expect(supportLink).toHaveAttribute('href', /support\.tb\.pro/);
    await expect(supportLink).toHaveAttribute('target', '_blank');
  }

  private async verifyOtherAppsSetupTab() {
    await this.getStartedSection.getByRole('tab', { name: 'Other Apps' }).click();
    await expect(this.getStartedSection.getByRole('tab', { name: 'Other Apps' })).toHaveAttribute('aria-selected', 'true');
    await expect(this.getStartedSection).toContainText('Automatic Configuration');
    await expect(this.getStartedSection).toContainText('Manual Configuration');
    await expect(this.getStartedSection).toContainText('Need Help?');

    const appPasswordLink = this.getStartedSection.getByRole('link', { name: 'app password' });
    await expect(appPasswordLink).toHaveAttribute('href', '#app-password-container');

    const supportLink = this.getStartedSection.getByRole('link', { name: 'Visit Support Article' });
    await expect(supportLink).toHaveAttribute('href', /support\.tb\.pro/);
    await expect(supportLink).toHaveAttribute('target', '_blank');

    await this.verifyServerSettingsValues(this.getStartedSection);
  }

  private async verifyServerSettingsValues(container: Locator) {
    const incomingServerCard = container.locator('.server-settings-card').filter({ hasText: 'Incoming server' });
    const outgoingServerCard = container.locator('.server-settings-card').filter({ hasText: 'Outgoing server' });

    await incomingServerCard.getByRole('button', { name: 'IMAP' }).click();
    await this.verifyServerCardValues(incomingServerCard, ACCTS_HOST, formatPort(IMAP_PORT, IMAP_TLS));

    await incomingServerCard.getByRole('button', { name: 'JMAP' }).click();
    await this.verifyServerCardValues(incomingServerCard, ACCTS_HOST, formatPort(JMAP_PORT, JMAP_TLS));

    await outgoingServerCard.getByRole('button', { name: 'SMTP' }).click();
    await this.verifyServerCardValues(outgoingServerCard, ACCTS_HOST, formatPort(SMTP_PORT, SMTP_TLS));
  }

  private async verifyServerCardValues(serverCard: Locator, expectedServer: string, expectedPort: string) {
    const serverValue = serverCard
      .locator('.server-detail-item')
      .filter({ hasText: 'SERVER:' })
      .locator('.server-detail-item-value span');
    const portValue = serverCard
      .locator('.server-detail-item')
      .filter({ hasText: 'PORT:' })
      .locator('.server-detail-item-value span');

    await expect(serverValue).toHaveText(expectedServer);
    await expect(portValue).toContainText(expectedPort);
  }

  private async verifyContactScreenDisplayed() {
    await this.waitForPageToSettle();
    await expect.poll(async () => new URL(this.page.url()).pathname).toMatch(/^\/contact\/?$/);
    await expect(this.contactHeader).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
  }

  private async waitForPageToSettle() {
    await waitForVueApp(this.page);
    await this.page.waitForLoadState('networkidle', { timeout: TIMEOUT_5_SECONDS }).catch(() => {});
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
  }

  private async getConfiguredServiceUrls(): Promise<ServiceUrls> {
    return await this.page.evaluate(() => ({
      mail: (window as any)._page?.webmailUrl,
      appointment: (window as any)._page?.tbProAppointmentUrl,
      send: (window as any)._page?.tbProSendUrl,
    }));
  }

  private async verifyPopupServiceAppLoads({
    link,
    expectedUrl,
    beforeExpectedElements = [],
    expectedElementName,
    expectedElement,
  }: PopupPageAssertion) {
    expect(expectedUrl).toBeTruthy();
    await link.scrollIntoViewIfNeeded();
    await expect(link).toHaveAttribute('href', expectedUrl);
    await expect(link).toHaveAttribute('target', '_blank');

    const [popup] = await Promise.all([
      this.page.waitForEvent('popup'),
      link.click({ timeout: TIMEOUT_30_SECONDS }),
    ]);

    await expect
      .poll(async () => new URL(popup.url()).origin, { timeout: TIMEOUT_60_SECONDS })
      .toBe(new URL(expectedUrl).origin);
    for (const beforeExpectedElement of beforeExpectedElements) {
      await expect(
        beforeExpectedElement.expectedElement(popup),
        `${beforeExpectedElement.expectedElementName} should be visible after navigating to ${expectedUrl}`,
      ).toBeVisible({ timeout: TIMEOUT_60_SECONDS }); // browserstack is super slow
    }
    if (expectedElement) {
      await expect(
        expectedElement(popup),
        `${expectedElementName} should be visible after navigating to ${expectedUrl}`,
      ).toBeVisible({ timeout: TIMEOUT_60_SECONDS }); // browserstack is super slow
    }
    await popup.close();
  }
}
