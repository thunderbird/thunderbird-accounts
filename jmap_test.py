"""MailClientJMAP test script. These examples are tested against a stand-alone Stalwart v0.16 instance.
The results and responses will be used in unit tests."""

from thunderbird_accounts.mail.clients.mail_client_jmap import MailClientAdminJMAP

jwt = None
client = MailClientAdminJMAP()
# user_client = MailClientUserJMAP(username='pizza666@example.org', user_jwt=jwt)


# print('account->', client.get_account('admin@example.org'))
# print('domain->', client.get_domain('example.com'))
print('set account->', client.create_account([], 'pizza@example.org', 'PIZZA!', quota=15_000))
print('delete account->', client.delete_account('pizza@example.org'))
# print('save email->', client.save_email_addresses('admin@example.org', ['lols2@example.com']))
# print('create domain->', client.create_domain('pizza.lol', 'weeee'))
# print('delete domain->', client.delete_domain('pizza.lol'))
# app_password = user_client.save_app_password('my cool device!!')
# print('create app password->', app_password)
# print('delete app password->', user_client.delete_app_password(app_password.id))
# print('save alias->', client.save_email_addresses('admin@example.org', ['pants123@example.org']))
# print('remove alias->', client.delete_email_addresses('admin@example.org', ['pants123@example.org']))
# print('???', user_client.get_identity())
# print('create dkim->',client.create_dkim('example.org'))

print('get dns record->', client._get_dns_records('example.org'))
print('build dns record->', client.build_expected_dns_records('example.org'))
print('check dns record->', client.check_domain_dns('faviconfetcher.ca'))

# print('->', AccountUpdate(aliases={'0': EmailAlias(enabled=True, name='beans', domain_id='g')}).model_dump())
