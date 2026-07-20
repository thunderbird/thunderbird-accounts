from thunderbird_accounts.mail.exceptions import DomainNotFoundError
from thunderbird_accounts.mail.clients.jmap_client import JMAPClient
from thunderbird_accounts.mail.clients.stalwart_types import DomainType
from thunderbird_accounts.mail.clients.jmap_types import JMapRequest, Invocation, ResponseIndex
from thunderbird_accounts.mail.clients.mail_client_interface import MailClientInterface


class MailClientJMAP(MailClientInterface):
    def __init__(self):
        self.client = JMAPClient('http://localhost:8080', 'admin', 'admin', JMAPClient.AUTH_TYPES.BASIC)
        self.account_id = None
        pass

    def _get_session(self):
        session = self.client.get_session()

        # Retrieve our account from the primary account for jmap calls
        self.account_id = session.get('primaryAccounts', {}).get('urn:stalwart:jmap')
        if not self.account_id:
            self.account_id = list(session.get('accounts', {}).keys())[0]

    def get_domain(self, domain) -> DomainType:
        response = self.client.request(JMapRequest(
            using=[
                'urn:ietf:params:jmap:core',
                'urn:stalwart:jmap',
            ],
            methodCalls=[
                Invocation(
                    'x:Domain/query',
                    {
                        'accountId': self.account_id,
                        'filter': {'name': domain},
                        'limit': 25,
                        'position': 0,
                        'calculateTotal': True,
                    },
                    '0',
                ),
                Invocation(
                    'x:Domain/get',
                    {
                        'accountId': self.account_id,
                        '#ids': {'resultOf': '0', 'name': 'x:Domain/query', 'path': '/ids'},
                    },
                    '1',
                ),
            ],
        ))


        if not response.methodResponses or response.methodResponses[0][ResponseIndex.DATA]['total'] == 0:
            raise DomainNotFoundError(domain)


        return DomainType(**{})
        # data = response.json()
        # error = data.get('error')

        # logging.info(f'[MailClient.get_domain({domain}]: {data}')

        # if error == StalwartErrors.NOT_FOUND.value:
        #    raise DomainNotFoundError(domain)

        # assert data.get('data', {}).get('type') == 'domain'

        # return data.get('data')
