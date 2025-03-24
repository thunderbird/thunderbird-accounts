import uuid

from io import StringIO

from django.core import management
from django.test import TestCase
from faker import Faker
from thunderbird_accounts.client import models


fake = Faker()


# Create your tests here.
class CreateClientCommands(TestCase):
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
        # this will in-turn also test the 'create_client_contact' command
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
        # this will in-turn also test the 'create_client_contact' and 'create_client_environment' commands
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

    def test_create_client_environment_multiple(self):
        existing_client = models.Client.objects.create(name=self.client_name)
        output = StringIO()
        env_list = ['env_one', 'env_two', 'env_three', 'env_four', 'env_five']

        # add each environment to existing client
        for next_env in env_list:
            management.call_command(
                'create_client_environment',
                existing_client.uuid,
                next_env,
                self.env_redirect_url,
                self.env_allowed_hostnames,
                stdout=output,
            )

            self.assertIn(
                f'Successfully created client environment {next_env} for {existing_client.uuid}', output.getvalue()
            )

        # verify all envs exist
        for next_env in env_list:
            try:
                client_env = models.ClientEnvironment.objects.get(
                    environment=f'{next_env}', redirect_url=self.env_redirect_url, client_id=existing_client.uuid
                )
            except models.ClientEnvironment.DoesNotExist:
                client_env = None

            self.assertTrue(client_env)

    def test_create_client_with_environment_missing_param(self):
        output = StringIO()

        management.call_command(
            'create_client',
            self.client_name,
            self.contact_name,
            self.contact_email,
            self.contact_url,
            env_type=self.env_type,
            env_allowed_hostnames=self.env_allowed_hostnames,
            stdout=output,
        )

        self.assertIn('A client environment requires all env_* options to be filled', output.getvalue())

        try:
            client = models.Client.objects.get(name=self.client_name)
        except models.Client.DoesNotExist:
            client = None

        self.assertFalse(client)

        client_query = models.Client.objects.filter(name=self.client_name)

        # Ensure that the query only equals the existing client
        self.assertFalse(client_query)

    def test_create_client_environment_when_client_not_exist(self):
        output = StringIO()
        fake_client_uuid = uuid.uuid4()

        management.call_command(
            'create_client_environment',
            fake_client_uuid,
            self.env_type,
            self.env_redirect_url,
            self.env_allowed_hostnames,
            stdout=output,
        )

        self.assertIn(f'Client: {fake_client_uuid} does not exist', output.getvalue())

    def test_create_duplicate_client_environment(self):
        new_client = models.Client.objects.create(name=self.client_name)
        same_env_type = 'some-env'
        same_redirect_url = 'https://env-name/example.org'
        same_allowed_hostnames = "['https://some-host/example.org', 'https://some-other-host/example.org']"

        output = StringIO()

        # add an environment to our existing client
        management.call_command(
            'create_client_environment',
            new_client.uuid,
            same_env_type,
            same_redirect_url,
            same_allowed_hostnames,
            stdout=output,
        )

        self.assertIn(
            f'Successfully created client environment {same_env_type} for {new_client.uuid}', output.getvalue()
        )

        try:
            client_env = models.ClientEnvironment.objects.get(
                environment=f'{same_env_type}', redirect_url=same_redirect_url, client_id=new_client.uuid
            )
        except models.ClientEnvironment.DoesNotExist:
            client_env = None

        self.assertTrue(client_env)

        # now attempt to add the exact same environment entry for the same client, expect failure
        management.call_command(
            'create_client_environment',
            new_client.uuid,
            same_env_type,
            same_redirect_url,
            same_allowed_hostnames,
            stdout=output,
        )

        self.assertIn(
            f'A client environment with identical details already exists for client {new_client.uuid}',
            output.getvalue(),
        )

        # ensure still only one environment for this client
        client_env_query = models.ClientEnvironment.objects.filter(client_id=new_client.uuid)
        self.assertQuerySetEqual(client_env_query, [client_env])

    def test_create_client_contact_when_client_not_exist(self):
        output = StringIO()
        fake_client_uuid = uuid.uuid4()

        management.call_command(
            'create_client_contact',
            fake_client_uuid,
            self.contact_name,
            self.contact_email,
            self.contact_url,
            stdout=output,
        )

        self.assertIn(f'Client: {fake_client_uuid} does not exist', output.getvalue())

    def test_create_duplicate_client_contact(self):
        new_client = models.Client.objects.create(name=self.client_name)
        output = StringIO()
        same_name = 'Some Person'
        same_email = 'someperson@example.org'
        same_url = 'http://www.firstlast.org'

        # add a contact to our existing client
        management.call_command(
            'create_client_contact', new_client.uuid, same_name, same_email, same_url, stdout=output
        )

        self.assertIn(f'Successfully created client contact {same_name} for {new_client.uuid}', output.getvalue())

        try:
            client_contact = models.ClientContact.objects.get(name=same_name, client_id=new_client.uuid)
        except models.ClientContact.DoesNotExist:
            client_contact = None

        self.assertTrue(client_contact)

        # now attempt to add the exact same contact entry for the same client, expect failure
        management.call_command(
            'create_client_contact', new_client.uuid, same_name, same_email, same_url, stdout=output
        )

        self.assertIn(
            f'A client contact with identical details already exists for client {new_client.uuid}', output.getvalue()
        )

        # ensure still only one contact for this client
        client_contact_query = models.ClientContact.objects.filter(client_id=new_client.uuid)
        self.assertQuerySetEqual(client_contact_query, [client_contact])
