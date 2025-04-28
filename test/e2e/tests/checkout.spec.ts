import { test, expect } from '@playwright/test';
import { CheckoutPage } from '../pages/checkout-page';
import { PaddleFrame } from '../pages/paddle-frame';
import { navigateToAccountsSelfServeHubAndSignIn } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  ACCTS_CHECKOUT_URL,
  CHECKOUT_POSTAL_CODE,
  CHECKOUT_EMAIL_ADDRESS,
  CHECKOUT_CC_NUM,
  CHECKOUT_CC_NAME,
  CHECKOUT_CC_EXP,
  CHECKOUT_CC_CVV,
  ACCTS_CHECKOUT_SUCCESS_URL,
  TIMEOUT_2_SECONDS,
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
    test.describe('with bad Paddle response', () => {
      test.beforeEach(async ({ page }) => {
        checkoutPage = new CheckoutPage(page);
        await navigateToAccountsSelfServeHubAndSignIn(page);
        await page.route('**/pricing-preview', async (route) => {
          await route.fulfill(MOCK_PRICING_RESPONSE_BAD);
        });
        await page.goto(ACCTS_CHECKOUT_URL);
      });
      test('shows error when SDK returns bad response', async ({ page }) => {
        const err = page.getByTestId('pricing-error');
        await expect(err).toBeVisible();
      });
    });

    test.describe('with good Paddle response', () => {
      test.beforeEach(async ({ page }) => {
        checkoutPage = new CheckoutPage(page);
        await navigateToAccountsSelfServeHubAndSignIn(page);
        await page.goto(ACCTS_CHECKOUT_URL);
      });

      test('shows correct products when SDK calls /pricing-preview', async ({ page }) => {
        await expect(checkoutPage.pricingGrid).toBeVisible();
        await expect(checkoutPage.priceCards).toHaveCount(3);
        await expect(checkoutPage.priceCards.nth(0)).toContainText('Small');
        await expect(checkoutPage.priceCards.nth(1)).toContainText('Medium');
        await expect(checkoutPage.priceCards.nth(2)).toContainText('Big');
      });

      test('able to complete a checkout', async ({ page }) => {
        // open modal for a product
        await checkoutPage.checkoutButtons.nth(0).click();

        // frame takes some time to load
        await page.waitForTimeout(TIMEOUT_2_SECONDS);
        paddleFrame = new PaddleFrame(page);

        // confirm that modal opens
        expect(paddleFrame.modal).toContainText('Order summary');

        // fill out form
        await paddleFrame.emailField.fill(CHECKOUT_EMAIL_ADDRESS, { timeout: TIMEOUT_2_SECONDS });
        await paddleFrame.countryField.selectOption(CHECKOUT_COUNTRY);
        await paddleFrame.postalCodeField.fill(CHECKOUT_POSTAL_CODE, { timeout: TIMEOUT_2_SECONDS });
        await paddleFrame.continueButton.click();

        await page.waitForTimeout(TIMEOUT_2_SECONDS);
        await paddleFrame.cardNumberField.fill(CHECKOUT_CC_NUM, { timeout: TIMEOUT_2_SECONDS });
        await paddleFrame.cardNameField.fill(CHECKOUT_CC_NAME, { timeout: TIMEOUT_2_SECONDS });
        await paddleFrame.cardExpiryField.fill(CHECKOUT_CC_EXP, { timeout: TIMEOUT_2_SECONDS });
        await paddleFrame.cardVerificationField.fill(CHECKOUT_CC_CVV, { timeout: TIMEOUT_2_SECONDS });

        await Promise.all([page.waitForURL(ACCTS_CHECKOUT_SUCCESS_URL), await paddleFrame.finalCheckoutButton.click()]);

        expect(page.url()).toBe(ACCTS_CHECKOUT_SUCCESS_URL);
      });
    });
  }
);
