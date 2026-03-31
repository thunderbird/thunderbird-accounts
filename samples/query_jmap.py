from thunderbird_accounts.mail.tiny_jmap_client import TinyJMAPClient
import base64
import pprint

"""
Simple script to query prod's jmap with an app password

Don't commit changes to this script, run in project directory with 

``uv run ./samples/query_jmap.py``

If you get a 401 unauthorized make sure you're using your thundermail address and correct app password!
"""

host = 'https://mail.thundermail.com'  # Prod
username = 'your thundermail address'
app_password = 'your app password'

plain_auth = base64.b64encode(f'{username}:{app_password}'.encode()).decode()
client = TinyJMAPClient(hostname=host, username=username, token=plain_auth, auth_type=TinyJMAPClient.AUTH_TYPES.BASIC)

account_id = client.get_account_id()

# Example: Return all of their mailboxes
inbox_res = client.make_jmap_call(
    {
        'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
        'methodCalls': [
            [
                'Mailbox/get',
                {
                    'accountId': account_id,
                },
                '0',
            ]
        ],
    }
)

print('Response:')  # noqa
pprint.pprint(inbox_res)
