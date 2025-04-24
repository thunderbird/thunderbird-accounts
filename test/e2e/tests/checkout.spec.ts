import { test, expect } from '@playwright/test';
import { CheckoutPage } from '../pages/checkout-page';
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
} from '../const/constants';
import { MOCK_PRICING_RESPONSE_BAD, MOCK_PRICING_RESPONSE_OK } from '../const/mocks/paddle';

let checkoutPage: CheckoutPage;

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
        const priceCards = page.getByTestId('pricing-grid-price-item');
        await expect(checkoutPage.pricingGrid).toBeVisible();
        await expect(priceCards).toHaveCount(3);
        await expect(priceCards.nth(0)).toContainText('Small');
        await expect(priceCards.nth(1)).toContainText('Medium');
        await expect(priceCards.nth(2)).toContainText('Big');
      });

      test('able to complete a checkout', async ({ page }) => {
        // open modal for a product
        const checkoutButtons = page.getByTestId('checkout-button');
        await checkoutButtons.nth(0).click();

        // frame takes some time to load
        await page.waitForTimeout(TIMEOUT_2_SECONDS);
        const paddleFrame = page.frame({ name: 'paddle_frame' });
        await expect(paddleFrame).not.toBeNull();
        if (!paddleFrame) {
          // serves as non-null type guard
          return;
        }

        // confirm that modal opens
        const modal = await paddleFrame.locator('body');
        expect(modal).toContainText('Order summary');

        // fill out form
        const emailField = modal.getByTestId('authenticationEmailInput');
        await emailField.fill(CHECKOUT_EMAIL_ADDRESS, { timeout: TIMEOUT_2_SECONDS });
        const postalCodeField = modal.getByTestId('postcodeInput');
        await postalCodeField.fill(CHECKOUT_POSTAL_CODE, { timeout: TIMEOUT_2_SECONDS });

        const continueButton = modal.getByTestId('combinedAuthenticationLocationFormSubmitButton');
        await continueButton.click();

        await page.waitForTimeout(TIMEOUT_2_SECONDS);
        const cardNumberField = modal.getByTestId('cardNumberInput');
        await cardNumberField.fill(CHECKOUT_CC_NUM, { timeout: TIMEOUT_2_SECONDS });
        const cardNameField = modal.getByTestId('cardholderNameInput');
        await cardNameField.fill(CHECKOUT_CC_NAME, { timeout: TIMEOUT_2_SECONDS });
        const cardExpiryField = modal.getByTestId('expiryDateField');
        await cardExpiryField.fill(CHECKOUT_CC_EXP, { timeout: TIMEOUT_2_SECONDS });
        const cardVerificationField = modal.getByTestId('cardVerificationValueInput');
        await cardVerificationField.fill(CHECKOUT_CC_CVV, { timeout: TIMEOUT_2_SECONDS });

        const finalCheckoutButton = modal.getByTestId('cardPaymentFormSubmitButton');

        await Promise.all([page.waitForURL(ACCTS_CHECKOUT_SUCCESS_URL), await finalCheckoutButton.click()]);

        expect(page.url()).toBe(ACCTS_CHECKOUT_SUCCESS_URL);
      });
    });
  }
);
