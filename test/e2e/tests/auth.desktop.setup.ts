import { test as setup } from '@playwright/test';

import path from 'path';

import { navigateToAccountsHubAndSignIn } from '../utils/utils';


const fs = require('fs');
const directoryPath = path.join(__dirname, '../test-results/.auth');

fs.mkdir(directoryPath, (err: any) => {
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

setup('desktop browser authenticate', async ({ page }) => {
  console.log('inside authenticate setup, about to call navigate and sign in');
  // Perform authentication steps
  await navigateToAccountsHubAndSignIn(page);

  // End of authentication steps, save the auth
  await page.context().storageState({ path: authFile });
});
