==================================
Intended Sequence
==================================

The following is up to date as of: Dec 5th, 2024

.. mermaid::

  sequenceDiagram
      User-->>+Service: Clicks Login
      Service-->>+TB Accounts: Requests Login URL with Service Secret
      TB Accounts-->>+Service: Sends one-time use login url
      Service-->>+User: Sends User to one-time use login url
      User-->>+TB Accounts: Lands on TB Accounts for authentication check

      alt If TB Accounts session auth is invalid or fxa creds are invalid
      TB Accounts-->>+FXA: Sends user to OAuth
      FXA-->>+TB Accounts: Saves FXA profile / FXA credentials
      end

      TB Accounts-->>+Service: Creates & sends user-scoped refresh/access token
      Service<<-->>+TB Accounts: Uses user-scoped access token to retrieve profile details
      Service-->>+User: Creates and passes Service user-scoped access token
      alt OR
      Service-->>+User: Passes TB Account's user-scoped access token
      end
