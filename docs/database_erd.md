## Database Entity Relational Diagram

The following is up to date as of: Nov 12th, 2024

```mermaid
erDiagram  

    %%{External APIs}%%
    FXA
	FXA ||..|{ User : connects

    "Django Authentication"
	"Django Authentication" ||..|{ User : connects

    "Auth Schemes"
    "Auth Schemes" ||..|| FXA : either
    "Auth Schemes" ||..|| "Django Authentication" : or


	%%{Authentication App}%%
	User {
		uuid uuid PK "UUID"
		string fxa_id "Firefox Account ID"
		string last_used_email "The last email used with Firefox Accounts"
		string display_name "FXA Display Name"
		string avatar_url "FXA Avatar URL"
		string timezone "Timezone (e.g. America/Vancouver, Europe/Berlin)"

		%%{Django defaults}%%
		string password "Login password, unused with fxa"
		string username "Login Username, unused with fxa"
		string email "Email"

        bool is_superuser "Is the user is a super user?"
		bool is_staff "Is the user staff?"
		bool is_active "Is the user active?"
		datetime date_joined "Date the user joined (UTC)"
		datetime last_login "Date the user last logged in (UTC)"

		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"
	}
	
	%%{Client App}%%
	Client {
		uuid uuid PK "UUID"
		string name "Client App's Name"

		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"
	}

	ClientContact {
		uuid uuid PK "UUID"
		string name "Contact Name"
		string email "Contact Email"
		string website "Contact Website"
		
		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"

        string client_id FK "Related Client ID"
	}
	Client ||--|{ ClientContact : has

    ClientEnvironment {
        uuid uuid PK "UUID"
        string environment "Environment the client is in (i.e. dev, stage, prod)"
		string redirect_url "URL to redirect the user after they login"
		string auth_token "Authentication token the client will use for server-to-server requests" 
        bool is_active "Is this environment active?"

		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"

        string client_id FK "Realted Client's ID"
    }

	ClientWebhook {
		uuid uuid PK "UUID"
		string name "Name associated with this webhook (organizational use only)"
		string webhook_url "URL of the webhook"
		enum type "Type of webhook [auth, subscription]"
		
		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"

        string client_environment_id FK "Related Client ID"
	}
	ClientEnvironment ||--o{ ClientWebhook : has

    Client ||--o{ ClientEnvironment : has

	%%{Subscription App}%%
	Customer {
		uuid uuid PK "UUID"
		string name "Customer Name"
		string email "Customer Email"

		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"

        string user_id FK "Related User's ID"
	}
    User ||--o{ Customer : has

	Subscription {
		uuid uuid PK "UUID"
		string name "Name"
		string paddle_id "Subscription's associated Paddle ID"
		bool is_active "Is this subscription active?"
		datetime active_since "Date since this subscription was active"
		datetime inactive_since "Date since this subscription was inactivated"

		datetime created_at "Datetime of model creation (UTC)"
		datetime updated_at "Datetime of last saved (UTC)"

		string customer_id FK "Related Customer UUID"
	}
	Customer ||--o{ Subscription : has
```