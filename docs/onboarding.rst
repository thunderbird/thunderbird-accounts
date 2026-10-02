Onboarding a New User
---------------------

This document describes the steps involved in onboarding a new user to Thunderbird Accounts, from the initial sign up through to a working mailbox.

=====================
Overview of the Flow
=====================

1. The user's recovery email is added to the allow list.
2. The user signs up via the sign up form and is created in Keycloak and Accounts.
3. The user accepts the ToS and Privacy terms and payment.

===============
Prerequisites
===============

* A recovery email address (doesn't have to be valid for local development)
* An entry on the allow list
* A Paddle plan setup in Django Admin

==============
Step by Step
==============

Step 1: Add the User to the Allow List
======================================

As an admin user (admin@example.org / admin, for local development), navigate to /admin/authentication/allowlistentry/ and add a new entry with the desired recovery email.

Then logout! Otherwise you will still be logged in as the admin user!

Step 2: Sign Up
===============

Navigate to `/sign-up?email=<recovery-email>` and follow the prompts. The last step will be to check the confirmation email. If you are using local dev, access Mailpit (usually at http://localhost:8025/) and click on the link in the email.

Step 3: Accept ToS / Privacy terms and pay
=================

You will be logged in and shown the ToS and Privacy terms for acceptance. After accepting, proceed to the payment step. If you are using local dev, access Paddle's test cards page (https://developer.paddle.com/concepts/payment-methods/credit-debit-card#test-payment-method) and fill the rest of the fields with any data.

At this point, you should have a provisioned Stalwart account ready to go!

