import { test, expect } from '@playwright/test';
import { CheckoutPage } from '../pages/checkout-page';
import { PaddleFrame } from '../pages/paddle-frame';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  CHECKOUT_POSTAL_CODE,
  CHECKOUT_EMAIL_ADDRESS,
  CHECKOUT_CC_NUM,
  CHECKOUT_CC_NAME,
  CHECKOUT_CC_EXP,
  CHECKOUT_CC_CVV,
  ACCTS_CHECKOUT_SUCCESS_URL,
  TIMEOUT_2_SECONDS,
  TIMEOUT_5_SECONDS,
  TIMEOUT_30_SECONDS,
  CHECKOUT_COUNTRY,
} from '../const/constants';
import { MOCK_PRICING_RESPONSE_BAD } from '../const/mocks/paddle';

let checkoutPage: CheckoutPage;
let paddleFrame: PaddleFrame;

test.describe(
  'self-serve hub checkout page',
  {
    tag: [PLAYWRIGHT_TAG_E2E_SUITE],
  },
  () => {
    test.describe('with bad Paddle response', { tag: '@paddle' },() => {
      test.beforeEach(async ({ page }) => {
        checkoutPage = new CheckoutPage(page);
        // we are already signed into accounts via our auth.setup
        await page.route('**/pricing-preview', async (route) => {
          await route.fulfill(MOCK_PRICING_RESPONSE_BAD);
        });
        await checkoutPage.navigateToCheckoutPage();
      });
      test('shows error when SDK returns bad response', async ({ page }) => {
        const err = page.getByTestId('pricing-error');
        await expect(err).toBeVisible();
      });
      test.afterEach(async ({ page }) => {
        // remove our mock/handler
        await page.unroute('**/pricing-preview');
        await page.waitForTimeout(TIMEOUT_2_SECONDS);
      });
    });

    test.describe('with good Paddle response', { tag: '@paddle' }, () => {
      test.beforeEach(async ({ page }) => {
        checkoutPage = new CheckoutPage(page);
        // we are already signed into accounts via our auth.setup
        await checkoutPage.navigateToCheckoutPage();
      });

      test('shows correct products when SDK calls /pricing-preview', async ({ page }) => {
        await expect(checkoutPage.pricingGrid).toBeVisible();
        await expect(checkoutPage.planCards).toHaveCount(3);
        await expect(checkoutPage.planCards.nth(0)).toContainText('Small');
        await expect(checkoutPage.planCards.nth(1)).toContainText('Medium');
        await expect(checkoutPage.planCards.nth(2)).toContainText('High');
      });

      test('able to complete a checkout', async ({ page }) => {
        // open modal for a product
        await checkoutPage.checkoutButtons.nth(0).click();

        // frame takes some time to load
        await page.waitForTimeout(TIMEOUT_2_SECONDS);
        paddleFrame = new PaddleFrame(page);

        // confirm that modal opens
        await expect(paddleFrame.modal).toContainText('Order summary');

        // fill out form
        await paddleFrame.emailField.fill(CHECKOUT_EMAIL_ADDRESS, { timeout: TIMEOUT_30_SECONDS });
        await paddleFrame.countryField.selectOption(CHECKOUT_COUNTRY);
        await paddleFrame.postalCodeField.fill(CHECKOUT_POSTAL_CODE, { timeout: TIMEOUT_5_SECONDS });
        await paddleFrame.continueButton.click();

        // next screen: payment info
        await page.waitForTimeout(TIMEOUT_5_SECONDS);
        await paddleFrame.cardNumberField.fill(CHECKOUT_CC_NUM, { timeout: TIMEOUT_30_SECONDS });
        await paddleFrame.cardNameField.fill(CHECKOUT_CC_NAME, { timeout: TIMEOUT_5_SECONDS });
        await paddleFrame.cardExpiryField.fill(CHECKOUT_CC_EXP, { timeout: TIMEOUT_5_SECONDS });
        await paddleFrame.cardVerificationField.fill(CHECKOUT_CC_CVV, { timeout: TIMEOUT_5_SECONDS });

       if (await paddleFrame.consentCheckBox.isVisible() && await paddleFrame.consentCheckBox.isEditable()) {
          await paddleFrame.consentCheckBox.check({ timeout: TIMEOUT_30_SECONDS });
          await page.waitForTimeout(TIMEOUT_2_SECONDS);
        }

        await paddleFrame.finalCheckoutButton.click();
        await page.waitForTimeout(TIMEOUT_5_SECONDS);
        await page.waitForURL(ACCTS_CHECKOUT_SUCCESS_URL, { timeout: TIMEOUT_30_SECONDS });
        expect(page.url()).toBe(ACCTS_CHECKOUT_SUCCESS_URL);
      });
    });
  }
);
