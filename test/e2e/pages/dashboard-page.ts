import { expect, type Locator, type Page } from '@playwright/test';
import {
  ACCTS_HUB_URL,
  ACCTS_OIDC_EMAIL,
  DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS,
  DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES,
  DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE,
  DASHBOARD_CURRENT_SUBSCRIPTION_PRICE,
  DASHBOARD_CURRENT_SUBSCRIPTION_SEND_STORAGE,
  PADDLE_HOST,
  TIMEOUT_2_SECONDS,
  TIMEOUT_3_SECONDS,
  TIMEOUT_5_SECONDS,
  TIMEOUT_30_SECONDS,
  TIMEOUT_60_SECONDS,
} from '../const/constants';
import { waitForVueApp } from '../utils/utils';

interface ServiceUrls {
  appointment: string;
  send: string;
}

type PopupPageAssertion = {
  serviceName: string;
  link: Locator;
  expectedUrl: string;
  expectedElementName: string;
  expectedElement: (page: Page) => Locator;
  beforeExpectedElements?: Array<{
    expectedElementName: string;
    expectedElement: (page: Page) => Locator;
  }>;
};

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export class DashboardPage {
  readonly page: Page;
  readonly myAccountHeading: Locator;
  readonly myAccountCard: Locator;
  readonly privacyAndDataHeading: Locator;
  readonly manageYourServicesHeading: Locator;
  readonly currentSubscriptionHeading: Locator;
  readonly currentSubscriptionSection: Locator;
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
    this.myAccountHeading = this.page.getByRole('heading', { name: 'My Account' });
    this.myAccountCard = this.page.locator('.my-account-card');
    this.privacyAndDataHeading = this.page.getByRole('heading', { name: 'Privacy & Data' });
    this.manageYourServicesHeading = this.page.getByRole('heading', { name: 'Manage Your Services' });
    this.currentSubscriptionHeading = this.page.getByRole('heading', { name: 'Your Current Subscription' });
    this.currentSubscriptionSection = this.page.locator('section').filter({ has: this.currentSubscriptionHeading });
    this.passwordChangeLink = this.page.locator('a[href="/reset-password/"]');
    this.updatePasswordHeader = this.page.getByRole('heading', { name: 'Update password' });
    this.deleteAccountLink = this.page.getByRole('link', { name: 'Delete account and all data' });
    this.thundermailLink = this.page.locator('.service-icon-link[href="/mail"]').filter({ hasText: 'Thundermail' });
    this.appointmentLink = this.page.locator('.service-icon-link').filter({ hasText: 'Appointment' });
    this.sendLink = this.page.locator('.service-icon-link').filter({ hasText: 'Send' });
    this.manageSubscriptionButton = this.page.getByRole('button', { name: 'Manage Subscription' });
    this.userAvatar = this.page.getByRole('banner').locator('.avatar');
    this.supportLink = this.page.getByRole('link', { name: 'Support' });
    this.logoutLink = this.page.getByRole('link', { name: 'Logout' });
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
    await expect(this.privacyAndDataHeading).toBeVisible();
    await expect(this.manageYourServicesHeading).toBeVisible();
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
}

  async verifyPasswordChangeNavigation() {
    await this.passwordChangeLink.click({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.updatePasswordHeader).toBeVisible({ timeout: TIMEOUT_60_SECONDS });
  }

  async verifyDeleteAccountNavigationOnly() {
    await this.deleteAccountLink.click();
    await this.verifyContactScreenDisplayed();
  }

  async verifyThundermailNavigation() {
    await this.thundermailLink.scrollIntoViewIfNeeded();
    await this.thundermailLink.click();
    await this.page.waitForTimeout(TIMEOUT_3_SECONDS);
    await this.waitForPageToSettle();
    await expect.poll(async () => new URL(this.page.url()).pathname).toBe('/mail');
    await expect(this.page.getByRole('heading', { name: 'Get started with Thundermail' })).toBeVisible({
      timeout: TIMEOUT_30_SECONDS,
    });
  }

  async verifyAppointmentAppLoadsAfterNavigation() {
    const serviceUrls = await this.getConfiguredServiceUrls();
    await this.verifyPopupServiceAppLoads({
      serviceName: 'Appointment',
      link: this.appointmentLink,
      expectedUrl: serviceUrls.appointment,
      beforeExpectedElements: [{
        expectedElementName: 'Need help? Visit support',
        expectedElement: page => page.locator('footer').getByRole('link', { name: /visit support/i }),
      }],
      expectedElementName: 'Copy booking link',
      expectedElement: page => page.getByRole('button', { name: /copy booking link/i }),
    });
  }

  async verifySendAppLoadsAfterNavigation() {
    const serviceUrls = await this.getConfiguredServiceUrls();
    await this.verifyPopupServiceAppLoads({
      serviceName: 'Send',
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

    try {
      await expect.poll(async () => popup.url()).not.toBe('about:blank');
      expect(new URL(popup.url()).protocol).toMatch(/^https?:$/);
      expect(new URL(popup.url()).host).toContain(PADDLE_HOST);
    } finally {
      if (!popup.isClosed()) {
        await popup.close().catch(() => {});
      }
    }
  }

  async verifyUserMenuControls() {
    await this.userAvatar.click();
    await expect(this.supportLink).toBeVisible();
    await expect(this.logoutLink).toBeVisible();
    await expect(this.logoutLink).toHaveAttribute('href', '/logout/');

    await this.supportLink.click();
    await this.verifyContactScreenDisplayed();
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
      appointment: (window as any)._page?.tbProAppointmentUrl,
      send: (window as any)._page?.tbProSendUrl,
    }));
  }

  private async verifyPopupServiceAppLoads({
    serviceName,
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

    const expectedOrigin = new URL(expectedUrl).origin;

    try {
      try {
        await expect
          .poll(
            async () => ({
              isExpectedOrigin: this.getUrlOrigin(popup.url()) === expectedOrigin,
              isAuthenticatedSignalVisible: await expectedElement(popup).isVisible().catch(() => false),
            }),
            {
              timeout: TIMEOUT_60_SECONDS,
              message: `waiting for ${serviceName} authentication to complete`,
            },
          )
          .toEqual({
            isExpectedOrigin: true,
            isAuthenticatedSignalVisible: true,
          });
      } catch (error) {
        const actualUrl = popup.isClosed() ? '<popup closed>' : this.sanitizeUrlForDiagnostics(popup.url());
        const pageTitle = popup.isClosed()
          ? '<unavailable>'
          : await popup.title().catch(() => '<unavailable>');
        const visibleHeadings = popup.isClosed()
          ? []
          : await popup.locator('h1:visible, h2:visible, h3:visible').allInnerTexts().catch(() => []);
        const headingSummary = visibleHeadings
          .map(heading => heading.replace(/\s+/g, ' ').trim())
          .filter(Boolean)
          .slice(0, 3)
          .join(' | ') || '<none>';

        throw new Error(
          `${serviceName} authentication did not complete. `
          + `Expected ${this.sanitizeUrlForDiagnostics(expectedUrl)} with visible `
          + `'${expectedElementName}', but the popup finished at ${actualUrl}. `
          + `Page title: '${pageTitle}'. Visible headings: '${headingSummary}'.`,
          { cause: error },
        );
      }

      console.log(
        `${serviceName} authenticated popup settled at ${this.sanitizeUrlForDiagnostics(popup.url())}`,
      );

      for (const beforeExpectedElement of beforeExpectedElements) {
        await expect(
          beforeExpectedElement.expectedElement(popup),
          `${beforeExpectedElement.expectedElementName} should be visible after navigating to ${expectedUrl}`,
        ).toBeVisible({ timeout: TIMEOUT_60_SECONDS }); // browserstack is super slow
      }
    } finally {
      if (!popup.isClosed()) {
        await popup.close().catch(() => {});
      }
    }
  }

  private getUrlOrigin(url: string): string | null {
    try {
      return new URL(url).origin;
    } catch {
      return null;
    }
  }

  private sanitizeUrlForDiagnostics(url: string): string {
    try {
      const sanitizedUrl = new URL(url);
      sanitizedUrl.search = '';
      sanitizedUrl.hash = '';
      return sanitizedUrl.toString();
    } catch {
      return url.split(/[?#]/, 1)[0];
    }
  }
}
