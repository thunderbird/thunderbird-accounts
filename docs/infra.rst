==================================
Infrastructure
==================================

The following is up to date as of: Jan 7th, 2025

Layout
------



Diagrams
--------

The entire authentication flow:

.. mermaid::

  sequenceDiagram
    participant User
    participant Service
    participant Cache
    participant TB Accounts
    participant FXA

    User-->>TB Accounts: Lands on TB Accounts for authentication check

    alt If TB Accounts session auth is invalid or fxa creds are invalid
    TB Accounts-->>FXA: Sends user to OAuth
    FXA-->>TB Accounts: Callback to TB Accounts
    end

    #opt Infra note
    #Service->TB Accounts: Share Session Secret(?)
    #end

    TB Accounts-->>Cache: Stores session id & cached user data

    TB Accounts-->>Service: Passes TB Account's session id
    Service-->>User: Passes TB Account's session id

    opt Service Authentication Check Flow
    User->>Service: Any auth-required request with session id
    Service->>Cache: Forward session id
    Cache->Cache: Ensure session id exists
    Service->Cache: Return latest user credentials if session is valid

    end

How services can validate authentication:

.. mermaid::
  sequenceDiagram
    participant User
    participant Service
    participant Cache
    participant TB Accounts
    participant FXA

    User->>Service: Any auth-required request with session id
    Service->>Cache: Forward session id
    Cache->Cache: Ensure session id exists
    Service->Cache: Return latest user credentials if session is valid


Overview of architecture:

.. mermaid::
  architecture-beta

      service fxa(cloud)[FXA]
      service tbaccounts(server)[TB Accounts]
      service cache(database)[Token Cache]
      service tbservice(server)[Service]


      fxa:L -- R:tbaccounts
      cache:B -- T:tbaccounts
      tbaccounts:L -- R:tbservice
      cache:L -- B:tbservice

