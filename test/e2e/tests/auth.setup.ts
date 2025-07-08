import { test as setup } from '@playwright/test';
import path from 'path';

import { navigateToAccountsSelfServeHubAndSignIn } from '../utils/utils';

import {
  ACCTS_SELF_SERVE_CONNECTION_INFO_URL,
  TIMEOUT_60_SECONDS,
} from "../const/constants";

const fs = require('fs');
const directoryPath = path.join(__dirname, '../test-results/.auth');

fs.mkdir(directoryPath, {recursive: true},(err: any) => {
  if (err) {
    console.error('error creating auth storage directory:', err);
    return
  }

  console.log('created auth storage directory');
  // when use storageState in browserstack yml, browserstack requires the file to exist already even on the
  // first time the auth-setup step is run; so must create an emtpy user.json file here
  const filepath = path.join(directoryPath, 'user.json');
  const emptyJsonObject = {};
  const jsonString = JSON.stringify(emptyJsonObject, null, 2); // The '2' adds indentation for readability
  fs.writeFileSync(filepath, jsonString);
});

// We write it here so it is blown away and re-created at the start of every test run; and is in .gitignore
const authFile = path.join(__dirname, '../test-results/.auth/user.json');

setup('authenticate', async ({ page }) => {
  console.log('inside authenticate setup, about to call navigate and sign in');
  // Perform authentication steps
  await navigateToAccountsSelfServeHubAndSignIn(page);

  // Wait until the page receives the cookies.
  // Sometimes login flow sets cookies in the process of several redirects.
  // Wait for the final URL to ensure that the cookies are actually set.
  await page.waitForURL(ACCTS_SELF_SERVE_CONNECTION_INFO_URL);
  await page.waitForTimeout(TIMEOUT_60_SECONDS);

  // End of authentication steps.
  await page.context().storageState({ path: authFile });
});
