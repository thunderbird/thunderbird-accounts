"""MailClientJMAP test script. These examples are tested against a stand-alone Stalwart v0.16 instance.
The results and responses will be used in unit tests."""
from thunderbird_accounts.mail.clients.mail_client_jmap import MailClientJMAP

client = MailClientJMAP()

print('account->', client.get_account('admin@example.org'))
# print('domain->', client.get_domain('example.com'))
# print('set account->', client.create_account([], 'pizza6662@example.org', 'PIZZA!', quota=15_000))
# print('delete account->', client.delete_account('pizza5@example.org'))
