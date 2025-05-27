import datetime
import enum

from thunderbird_accounts.subscription.decorators import inject_paddle

try:
    from paddle_billing import Client
except ImportError:
    Client = None


class PaddleCommand:
    class ReturnCodes(enum.StrEnum):
        OK = 'OK'
        ERROR = 'ERROR'  # Generic error, shouldn't normally be set
        NOT_SETUP = 'NOT_SETUP'

    def retrieve_paddle_data(self, paddle: Client):
        """Return a paddle object's .list() return value."""
        raise NotImplementedError

    def transform_paddle_data(self, paddle_obj) -> dict:
        """Return a dict that will be passed in an update_or_create's default parameter.
        paddle_obj is an instance of a Paddle API object."""
        raise NotImplementedError

    def get_model(self):
        """Return the model that will be affected by this operation.
        Not an instance, just the class."""
        raise NotImplementedError

    def add_arguments(self, parser):
        parser.add_argument('--dry', help="Don't update anything.", action='store_true')

    @inject_paddle
    def handle(self, paddle: Client, *args, **options):
        model = self.get_model()
        model_name = model.__name__

        if not paddle:
            self.stdout.write(self.style.NOTICE('Paddle is not setup.'))
            return self.ReturnCodes.NOT_SETUP

        dry_run = options.get('dry', False)
        verbosity = options.get('verbosity', 1)

        paddle_objs = self.retrieve_paddle_data(paddle)

        retrieved = 0
        created = 0
        updated = 0
        ignored = 0

        occurred_at = datetime.datetime.now(datetime.UTC)

        # This may call additional pages on iteration
        for paddle_obj in paddle_objs:
            retrieved += 1
            if dry_run:
                continue

            paddle_id = paddle_obj.id

            # Not really needed, but we don't have any locks setup so there's a slim chance we could run into update
            # timing shenanigans with webhooks.
            try:
                obj = model.objects.filter(paddle_id=paddle_id).filter(webhook_updated_at__gt=occurred_at).get()
                if obj:
                    ignored += 1
                    continue
            except model.DoesNotExist:
                pass

            model_data = self.transform_paddle_data(paddle_obj)

            # Okay now we can just do a big update.
            product, product_created = model.objects.update_or_create(
                paddle_id=paddle_id,
                defaults={
                    **model_data,
                    'webhook_updated_at': occurred_at,
                },
            )

            if product_created:
                created += 1
            else:
                updated += 1

        if verbosity > 0:
            self.stdout.write(self.style.SUCCESS(f'Finished retrieving Paddle {model_name}:'))
            self.stdout.write(self.style.SUCCESS(f'* {retrieved} {model_name} objects retrieved from Paddle API.'))
            self.stdout.write(self.style.SUCCESS(f'* {created} {model_name} models created.'))
            self.stdout.write(self.style.SUCCESS(f'* {updated} {model_name} models updated.'))
            self.stdout.write(
                self.style.SUCCESS(f'* {ignored} {model_name} models ignored due to data being older than db.')
            )

        return self.ReturnCodes.OK.value
