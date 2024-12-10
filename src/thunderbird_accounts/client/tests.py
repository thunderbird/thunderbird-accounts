from io import StringIO

from django.core import management
from django.test import TestCase
from faker import Faker
from thunderbird_accounts.client import models


fake = Faker()


# Create your tests here.
class CreateClientCommand(TestCase):
    def setUp(self):
        super().setUp()

        self.client_name = fake.hostname()
        self.contact_name = fake.name()
        self.contact_email = fake.email()
        self.contact_url = fake.url()
        self.env_type = fake.random_element(['dev', 'stage', 'prod', 'mystery'])
        self.env_redirect_url = fake.url()
        self.env_allowed_hostnames = ','.join([fake.url(), fake.url()])

    def test_create_client(self):
        management.call_command(
            'create_client', self.client_name, self.contact_name, self.contact_email, self.contact_url
        )

        try:
            client = models.Client.objects.get(name=self.client_name)
        except models.Client.DoesNotExist:
            client = None

        self.assertTrue(client)

        try:
            client_contact = models.ClientContact.objects.get(name=self.contact_name, client_id=client.uuid)
        except models.ClientContact.DoesNotExist:
            client_contact = None

        self.assertTrue(client_contact)

    def test_create_client_with_environment(self):
        management.call_command(
            'create_client',
            self.client_name,
            self.contact_name,
            self.contact_email,
            self.contact_url,
            env_type=self.env_type,
            env_redirect_url=self.env_redirect_url,
            env_allowed_hostnames=self.env_allowed_hostnames,
        )

        try:
            client = models.Client.objects.get(name=self.client_name)
        except models.Client.DoesNotExist:
            client = None

        self.assertTrue(client)

        try:
            client_contact = models.ClientContact.objects.get(name=self.contact_name, client_id=client.uuid)
        except models.ClientContact.DoesNotExist:
            client_contact = None

        self.assertTrue(client_contact)

        try:
            client_env = models.ClientEnvironment.objects.get(
                environment=self.env_type, redirect_url=self.env_redirect_url, client_id=client.uuid
            )
        except models.ClientEnvironment.DoesNotExist:
            client_env = None

        self.assertTrue(client_env)

    def test_create_client_when_client_already_exists(self):
        existing_client = models.Client.objects.create(name=self.client_name)

        output = StringIO()
        management.call_command(
            'create_client', self.client_name, self.contact_name, self.contact_email, self.contact_url, stdout=output
        )

        self.assertIn(f'A client with the name {existing_client.name} already exists', output.getvalue())

        client_query = models.Client.objects.filter(name=self.client_name)

        # Ensure that the query only equals the existing client
        self.assertQuerySetEqual(client_query, [existing_client])
