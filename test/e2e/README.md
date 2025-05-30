# Thunderbird Accounts E2E Tests

Guide for running the Thunderbird Accounts E2E tests.

## Installation

First install the E2E suite (includes Playwright):

```bash
cd test/e2e
npm install
```

Next install the Playwright browsers (Playwright uses it's own bundled browers) still in `test/e2e`:

```bash
npx playwright install
```

## E2E Test Prerequisites

The E2E tests require an existing FxA account used to sign-in to TB Accounts, and reads this from your local .env file. This includes:

- Credentials for an existing Accounts (FxA) account (email address, password)

In addition, you will need the env vars for the Paddle sandbox.
These can be found in the Services vault in 1Password in the secure note "Paddle Sandbox env vars".

## Running the E2E tests against your local dev environment

### Add Paddle env vars

In the top level `.env` file, add the values from the "Paddle Sandbox env vars" secure note.

```dotenv
PADDLE_TOKEN=<token>
PADDLE_API=<token>
PADDLE_ENV=sandbox
```

### Add FxA Account Information

When running the TB Accounts local dev stack it uses the FxA stage env for sign-in, and then redirects back to your localhost afterwords. So you will use your FxA stage test account also when running the E2E tests against your local dev stack.

First copy over the provided `.env.dev.example` to a local `.env`:

```bash
cd test/e2e
cp .env.dev.example .env
```

Then edit your local `.env` file and provide the following values:

```dotenv
ACCTS_FXA_EMAIL=<existing-stage-FxA-user-email>
ACCTS_FXA_PWORD=<exisiting-stage-FxA-user-password>
```

## Setup Paddle backend for subscription tests (optional)

Retrieve the 3 product ids from the Paddle secure note in 1password and run the following command with each product id 
while docker is running:

```bash
docker-compose exec backend ./manage.py create_plan_for_e2e_test <Plan Name> <Product ID>

# Example/
docker-compose exec backend ./manage.py create_plan_for_e2e_test Low pro_23edfsndfgjsn3kjn234n
```

### Run the tests

To run the E2E tests headless (still in `test/e2e`):

```bash
npm run e2e-test
```

To run the E2E tests with a UI so you can watch the tests run (still in `test/e2e`):

```bash
npm run e2e-test-headed
```

To run the E2E tests in debug mode (still in `test/e2e`):

```bash
npm run e2e-test-debug
```

#### Skipping Paddle tests

If you don't want to or cannot setup the backend for Paddle you can skip the Paddle specific tests by adding the param 
`--grep-invert @paddle` to the test command. 

```bash
npm run e2e-test -- --grep-invert @paddle
```

## Running the E2E tests against the stage environmnent

`Prerequisite`: When running the tests on the stage env, the TB Accounts test account must have a Thundermail email address already set up.

First copy over the provided `.env.stage.example` to a local `.env`:

```bash
cd test/e2e
cp .env.stage.example .env
```

Then edit your local `.env` file and provide the following values:

```dotenv
ACCTS_FXA_EMAIL=<existing-stage-FxA-user-email>
ACCTS_FXA_PWORD=<exisiting-stage-FxA-user-password>
THUNDERMAIL_USERNAME<thundermail username associated with the above acct>
THUNDERMAIL_EMAIL_ADDRESS=<thundermail email address associated with the above acct>
```

To run the E2E tests headless (still in `test/e2e`):

```bash
npm run e2e-test
```

To run the E2E tests with a UI so you can watch the tests run (still in `test/e2e`):

```bash
npm run e2e-test-headed
```

To run the E2E tests in debug mode (still in `test/e2e`):

```bash
npm run e2e-test-debug
```

## Running on BrowserStack

You can run the E2E tests from your local machine pointed at the stage environment, but against browsers provided in the BrowserStack Automate cloud.

<b>For security reasons when running the tests on BrowserStack I recommend that you use a dedicated test TB Accounts FxA account / credentials (NOT your own personal TB Acccounts / FxA credentials).</b>

Once you have credentials for an existing TB Accounts test account, edit your local `.env` file (that you first copied from `.env.stage.example`) and add these details (more information found above):

```dotenv
ACCTS_FXA_EMAIL=<existing-stage-FxA-user-email>
ACCTS_FXA_PWORD=<exisiting-stage-FxA-user-password>
THUNDERMAIL_USERNAME<thundermail username associated with the above acct>
THUNDERMAIL_EMAIL_ADDRESS=<thundermail email address associated with the above acct>
```

Also in order to run on BrowserStack you need to provide your BrowserStack credentials. Sign into your BrowserStack account and navigate to your `User Profile` and find your auth username and access key. In your local terminal export the following env vars to set the BrowserStack credentials that the tests will use:

```bash
export BROWSERSTACK_USERNAME=<your-browserstack-user-name>
```

```bash
export BROWSERSTACK_ACCESS_KEY=<your-browserstack-access-key>
```

To run the E2E tests on BrowserStack (still in `test/e2e`):

```bash
npm run e2e-test-browserstack
```

After the tests finish in your local console you'll see a link to the BrowserStack test session; when signed into your BrowserStack account you'll be able to use that link to see the test session results including video playback.

## Debugging E2E Test Failures

Here is some advice for how to investigate E2E test failures.

### E2E Tests Failing on your Local Dev Environment

If you are running the E2E tests on your local machine against your local development environment and the tests are failing, you can:

- Look at the playwright HTML report by running `npx playwright show-report` in test/e2e/
- Run the tests again this time in debug (UI) mode (see above)
  - In the debug mode browser expand each test that was ran, and review each test step to trace the test progress and failure
  - Look at the corresponding screenshots to get a visual of where and when the tests actually failed
  - Try to correlate the test failure with any local code changes

### E2E Tests Failing in CI on your PR Check

If you pushed to a branch or PR and the resulting Github pull request E2E test job check is failing, you can:

- In your PR scroll down to the 'Checks' section and click on the failed E2E test job
- In the console view, expand the E2E tests step and read the test failure details
- Check if a playwright report artifact exists:
  - In the console view click on `Summary` (top left)
  - This shows the GHA summary, at the bottom of the page look for an `Artifacts` section and click on `playwright-report` and download the ZIP
  - Open the ZIP file, expand it, and open the `index.html` file in your browser
