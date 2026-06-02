import { expect, type Locator, type Page } from '@playwright/test';
import {
  ACCTS_HOST,
  ACCTS_HUB_URL,
  DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS,
  DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES,
  DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE,
  IMAP_PORT,
  IMAP_TLS,
  JMAP_PORT,
  JMAP_TLS,
  PRIMARY_THUNDERMAIL_EMAIL,
  SMTP_PORT,
  SMTP_TLS,
  TIMEOUT_1_SECOND,
  TIMEOUT_2_SECONDS,
  TIMEOUT_5_SECONDS,
  TIMEOUT_30_SECONDS,
} from '../const/constants';
import { waitForVueApp } from '../utils/utils';

const hasTls = (tls: string) => Boolean(tls && tls !== 'None' && tls !== 'undefined');
const formatPort = (port: number, tls: string) => `${port}${hasTls(tls) ? ' (SSL/TLS)' : ''}`;
const TEST_EMAIL_ALIAS_LOCAL_PART_PREFIX = 'testalias';

export class MailPage {
  readonly page: Page;
  readonly mailView: Locator;
  readonly welcomeContainer: Locator;
  readonly planInfoContainer: Locator;
  readonly getStartedSection: Locator;
  readonly emailSettingsSection: Locator;
  readonly customDomainsSection: Locator;
  readonly serverSettingsAccordion: Locator;
  readonly displayNameSection: Locator;
  readonly appPasswordSection: Locator;
  readonly emailAliasesSection: Locator;
  readonly subscriptionErrorText: Locator;

  constructor(page: Page) {
    this.page = page;
    this.mailView = this.page.locator('.mail-view');
    this.welcomeContainer = this.page.locator('.welcome-container');
    this.planInfoContainer = this.page.locator('.plan-info-container');
    this.getStartedSection = this.page.locator('#connect-email');
    this.emailSettingsSection = this.page.locator('section#email-settings');
    this.customDomainsSection = this.page.locator('section#custom-domains');
    this.serverSettingsAccordion = this.emailSettingsSection.locator('.accordion').filter({ hasText: 'View server settings' });
    this.displayNameSection = this.emailSettingsSection.locator('.display-name-content');
    this.appPasswordSection = this.emailSettingsSection.locator('#app-password-container');
    this.emailAliasesSection = this.emailSettingsSection.locator('.email-aliases-content');
    this.subscriptionErrorText = this.page.getByText('Failed to load subscription information');
  }

  async navigateToMail() {
    await this.page.goto(`${ACCTS_HUB_URL}/mail`);
    await this.waitForPageToSettle();
    await expect.poll(async () => new URL(this.page.url()).pathname).toBe('/mail');
    await this.dismissQuickTourIfVisible();
  }

  async verifyWelcomeDashboardDisplayed() {
    await expect(this.mailView).toBeVisible();
    await expect(this.welcomeContainer.getByText('Welcome')).toBeVisible();
    await expect(this.welcomeContainer).toContainText(PRIMARY_THUNDERMAIL_EMAIL);

    const userDisplayName = await this.page.evaluate(() => (window as any)._page?.userDisplayName || '');
    await expect(this.welcomeContainer.locator('.name')).toBeVisible();
    if (userDisplayName) {
      await expect(this.welcomeContainer.locator('.name')).toContainText(userDisplayName);
    }

    await expect(this.subscriptionErrorText).not.toBeVisible();
    await expect(this.planInfoContainer.locator('.plan-name')).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.planInfoContainer.locator('.plan-storage')).toContainText(
      new RegExp(`of\\s+${this.escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_MAIL_STORAGE)}`),
    );
  }

  async verifyGetStartedComponents() {
    await this.getStartedSection.scrollIntoViewIfNeeded();
    await expect(this.getStartedSection.getByRole('heading', { name: 'Get started with Thundermail' })).toBeVisible();
    await expect(this.getStartedSection).toContainText('Connect your new email address to start sending and receiving.');

    await this.verifyPinToggle();
    await this.verifyDesktopSetupTab();
    await this.verifyMobileSetupTab();
    await this.verifyOtherAppsSetupTab();
  }

  async verifyEmailSettingsComponents() {
    await this.emailSettingsSection.scrollIntoViewIfNeeded();
    await expect(this.emailSettingsSection.getByRole('heading', { name: 'Email Settings' })).toBeVisible();
    await expect(this.emailSettingsSection).toContainText('Primary email');
    await expect(this.emailSettingsSection).toContainText(PRIMARY_THUNDERMAIL_EMAIL);

    await this.verifyDisplayNameFormOpensAndCancels();
    await this.verifyAppPasswordFormOpensAndCancels();
    await this.verifyEmailAliasFormOpensAndCancels();
    await this.verifyCanAddAndDeleteEmailAlias();
    await this.verifyServerSettings();
  }

  async verifyCustomDomainsComponents() {
    await this.customDomainsSection.scrollIntoViewIfNeeded();
    await expect(this.customDomainsSection.getByRole('heading', { name: 'Custom Domains' })).toBeVisible();
    await expect(this.customDomainsSection).toContainText('Use your own domain to create personalized email addresses.');
    await expect(this.customDomainsSection.locator('strong')).toContainText(
      new RegExp(`/\\s*${this.escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS)}\\s+domains added`),
    );

    await this.verifyCustomDomainActionMenuIfPresent();
    await this.verifyAddDomainFormCanOpen();
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

    await this.verifyOtherAppsManualConfigurationServerSettings();
  }

  private async verifyDisplayNameFormOpensAndCancels() {
    await expect(this.displayNameSection).toContainText('Display name');
    await this.displayNameSection.getByRole('button', { name: 'change' }).click();
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

  private async verifyEmailAliasFormOpensAndCancels() {
    await this.emailAliasesSection.scrollIntoViewIfNeeded();
    await expect(this.emailSettingsSection.getByRole('button', { name: 'Email aliases' })).toBeVisible();
    await expect(this.emailAliasesSection).toContainText(PRIMARY_THUNDERMAIL_EMAIL);
    await expect(this.emailAliasesSection.locator('.email-aliases-count-text').filter({ hasText: 'aliases used' })).toContainText(
      new RegExp(`of\\s+${this.escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES)}\\s+aliases used`),
    );
    const primaryAliasRow = this.emailAliasesSection.locator('.alias-item').filter({ hasText: PRIMARY_THUNDERMAIL_EMAIL });
    await expect(primaryAliasRow).toBeVisible();
    await expect(primaryAliasRow).toContainText('Primary');
    await expect(primaryAliasRow).toContainText('Subscription');

    const addAliasButton = this.emailAliasesSection.getByRole('button', { name: 'Add email alias' });
    if (await addAliasButton.isVisible()) {
      await addAliasButton.click();
      await expect(this.emailAliasesSection.locator('input[name="email-alias"]')).toBeVisible();
      const domainSelect = this.emailAliasesSection.locator('select[name="domain"]');
      await expect(domainSelect).toBeVisible();
      expect(ACCTS_HOST).toContain(await domainSelect.inputValue());
      await expect(this.emailAliasesSection.getByRole('button', { name: 'Submit' })).toBeVisible();
      await this.emailAliasesSection.getByRole('button', { name: 'Cancel' }).click();
      await expect(this.emailAliasesSection.locator('input[name="email-alias"]')).not.toBeVisible();
    }
  }

  private async verifyCanAddAndDeleteEmailAlias() {
    const aliasUsageText = await this.emailAliasesSection.locator('.email-aliases-count-text').filter({ hasText: 'aliases used' }).first().innerText();
    const aliasUsageMatch = aliasUsageText.match(/(\d+)\s+of\s+(\d+)\s+aliases used/i);
    if (!aliasUsageMatch) {
      throw new Error(`Could not determine alias usage from text: "${aliasUsageText}"`);
    }

    const aliasesUsed = Number(aliasUsageMatch[1]);
    const aliasLimit = Number(aliasUsageMatch[2]);
    if (aliasesUsed >= aliasLimit) {
      console.log('Skipping add/delete alias test because the maximum number of aliases are already in use.');
      return;
    }

    const addAliasButton = this.emailAliasesSection.getByRole('button', { name: 'Add email alias' });
    await expect(addAliasButton).toBeVisible();
    await addAliasButton.click();

    let aliasInput = this.emailAliasesSection.locator('input[name="email-alias"]');
    let domainSelect = this.emailAliasesSection.locator('select[name="domain"]');
    await expect(aliasInput).toBeVisible();
    await expect(domainSelect).toBeVisible();

    const selectedDomain = await domainSelect.inputValue();
    expect(ACCTS_HOST).toContain(selectedDomain);

    const testAliasLocalPart = `${TEST_EMAIL_ALIAS_LOCAL_PART_PREFIX}${Date.now()}`;
    const testAliasEmail = `${testAliasLocalPart}@${selectedDomain}`;
    const existingTestAliasRow = this.getEmailAliasRow(testAliasEmail);
    if (await existingTestAliasRow.count() > 0 && await existingTestAliasRow.isVisible()) {
      await this.emailAliasesSection.getByRole('button', { name: 'Cancel' }).click();
      await this.deleteEmailAlias(testAliasEmail);
      await this.page.waitForTimeout(TIMEOUT_1_SECOND);

      await addAliasButton.click();
      aliasInput = this.emailAliasesSection.locator('input[name="email-alias"]');
      domainSelect = this.emailAliasesSection.locator('select[name="domain"]');
      await expect(aliasInput).toBeVisible();
      await expect(domainSelect).toBeVisible();
      expect(await domainSelect.inputValue()).toBe(selectedDomain);
    }

    await aliasInput.fill(testAliasLocalPart);
    await this.emailAliasesSection.getByRole('button', { name: 'Submit' }).click();
    await this.page.waitForTimeout(TIMEOUT_1_SECOND);

    const testAliasRow = this.getEmailAliasRow(testAliasEmail);
    await expect(testAliasRow).toBeVisible();
    await expect(testAliasRow).not.toContainText('Primary');
    await expect(testAliasRow).not.toContainText('Subscription');

    await this.deleteEmailAlias(testAliasEmail);
    await this.page.waitForTimeout(TIMEOUT_1_SECOND);
    await expect(testAliasRow).not.toBeVisible();
  }

  private getEmailAliasRow(emailAlias: string) {
    return this.emailAliasesSection.locator('.alias-item').filter({ hasText: emailAlias });
  }

  private async deleteEmailAlias(emailAlias: string) {
    const aliasRow = this.getEmailAliasRow(emailAlias);
    await expect(aliasRow).toBeVisible();
    await aliasRow.locator('.kebab-menu-button').click();
    await aliasRow.getByRole('button', { name: 'Delete' }).click();
  }

  private async verifyServerSettings() {
    await this.serverSettingsAccordion.scrollIntoViewIfNeeded();
    await this.serverSettingsAccordion.getByRole('button', { name: 'View server settings' }).click();
    await expect(this.serverSettingsAccordion).toContainText('Incoming server');
    await expect(this.serverSettingsAccordion).toContainText('Outgoing server');
    await this.verifyServerSettingsValues(this.serverSettingsAccordion);
  }

  private async verifyOtherAppsManualConfigurationServerSettings() {
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

  private async verifyCustomDomainActionMenuIfPresent() {
    const actionButtons = this.customDomainsSection.locator('.custom-domain-item .kebab-menu-button');
    if (await actionButtons.count() === 0) {
      return;
    }

    const firstDomain = this.customDomainsSection.locator('.custom-domain-item').first();
    await expect(firstDomain).toContainText(/Verified|Pending|Failed/);
    await actionButtons.first().click();
    await expect(this.customDomainsSection.getByRole('button', { name: 'View DNS records' })).toBeVisible();
    await expect(this.customDomainsSection.getByRole('button', { name: /Verify|Re-verify/ })).toBeVisible();
    await expect(this.customDomainsSection.getByRole('button', { name: 'Delete' })).toBeVisible();
    await this.customDomainsSection.getByRole('heading', { name: 'Custom Domains' }).click();
  }

  private async verifyAddDomainFormCanOpen() {
    const addDomainButton = this.customDomainsSection.getByRole('button', { name: 'Add domain' });
    if (await addDomainButton.count() === 0 || !(await addDomainButton.isVisible())) {
      return;
    }

    await addDomainButton.click();
    await expect(this.customDomainsSection.locator('input[name="custom-domain"]')).toBeVisible();
    await expect(this.customDomainsSection.getByRole('button', { name: 'Continue' })).toBeVisible();
  }

  private async waitForPageToSettle() {
    await waitForVueApp(this.page);
    await this.page.waitForLoadState('networkidle', { timeout: TIMEOUT_5_SECONDS }).catch(() => {});
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
  }

  private async dismissQuickTourIfVisible() {
    const quickTour = this.page.locator('[data-tour-card]');
    if (await quickTour.isVisible()) {
      await quickTour.getByRole('button', { name: 'Skip' }).click();
      await expect(quickTour).not.toBeVisible();
    }
  }

  private escapeRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}
