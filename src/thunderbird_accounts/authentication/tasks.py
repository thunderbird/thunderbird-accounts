import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.celery.exceptions import TaskFailed
from thunderbird_accounts.subscription.models import Subscription
from thunderbird_accounts.subscription.tasks import add_or_tag_mailchimp_member
from thunderbird_accounts.authentication.utils import delete_user_data

logger = logging.getLogger(__name__)


def get_stale_incomplete_signup_users(cutoff_hours: int = settings.ABANDONED_CART_TAG_HOURS) -> QuerySet[User]:
    """Incomplete sign-ups older than the cutoff hours."""
    cutoff = timezone.now() - timedelta(hours=cutoff_hours)
    has_subscription = Subscription.objects.filter(user_id=OuterRef('pk'))
    return (
        User.objects.filter(
            created_at__lt=cutoff,
            is_test_account=False,
            is_staff=False,
            is_superuser=False,
            is_awaiting_payment_verification=False,
        )
        .annotate(has_subscription=Exists(has_subscription))
        .filter(has_subscription=False)
    )


@shared_task(bind=True)
def tag_abandoned_cart_in_mailchimp(self):
    """Tag abandoned sign-up users with abandoned_cart in Mailchimp."""
    if not settings.USE_MAILCHIMP:
        return {
            'task_status': 'skipped',
            'tagged': 0,
            'errors': 0,
            'skipped': 0,
        }

    tagged = 0
    errors = 0
    skipped = 0
    language_fallback = settings.DEFAULT_LANGUAGE
    mailchimp_language_map = settings.ACCOUNTS_TO_MAILCHIMP_LANGUAGES
    mailchimp_tag = settings.ABANDONED_CART_MAILCHIMP_TAG

    for user in get_stale_incomplete_signup_users().iterator():
        try:
            if user.subscription_set.exists():
                skipped += 1
                logger.info(
                    f'tag_abandoned_cart_in_mailchimp: skipped {user.uuid} because a subscription exists',
                )
                continue

            if user.is_awaiting_payment_verification:
                skipped += 1
                logger.info(
                    f'tag_abandoned_cart_in_mailchimp: skipped {user.uuid} because payment verification is pending',
                )
                continue

            if not user.recovery_email:
                skipped += 1
                logger.info(
                    f'tag_abandoned_cart_in_mailchimp: skipped {user.uuid} because recovery_email is blank',
                )
                continue

            language = mailchimp_language_map.get(user.language) or language_fallback
            add_or_tag_mailchimp_member(
                user.recovery_email,
                mailchimp_tag,
                language=language,
                error_context={'user_uuid': str(user.uuid)},
            )
        except TaskFailed as ex:
            errors += 1
            logger.warning(
                f'tag_abandoned_cart_in_mailchimp: mailchimp error for {user.uuid}: {ex.reason}',
            )
            continue
        except Exception as ex:
            errors += 1
            logger.exception(f'tag_abandoned_cart_in_mailchimp: failed to tag {user.uuid}: {ex.reason}')
            continue
        else:
            tagged += 1

    result = {
        'task_status': 'completed',
        'tagged': tagged,
        'errors': errors,
        'skipped': skipped,
    }
    logger.info('tag_abandoned_cart_in_mailchimp: %s', result)


@shared_task(bind=True)
def purge_incomplete_signups(self):
    """Delete abandoned sign-up users older than INCOMPLETE_SIGNUP_PURGE_HOURS.

    Only targets users with no Subscription records (including lapsed/canceled).
    """
    deleted = 0
    errors = 0

    for user in get_stale_incomplete_signup_users(cutoff_hours=settings.INCOMPLETE_SIGNUP_PURGE_HOURS).iterator():
        purge_errors = delete_user_data(user)
        if purge_errors:
            errors += 1
            logging.warning(
                'purge_incomplete_signups: partial deletion for %s: %s',
                user.username,
                purge_errors,
            )
        else:
            deleted += 1

    result = {
        'task_status': 'completed',
        'deleted': deleted,
        'errors': errors,
    }
    logging.info('purge_incomplete_signups: %s', result)
    return result
