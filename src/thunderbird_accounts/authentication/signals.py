import logging

from django.db.models.signals import post_delete, pre_save
from django.dispatch.dispatcher import receiver

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.authentication.utils import delete_cache_allow_list_entry


@receiver(post_delete, sender=User)
def user_post_delete(instance, **kwargs):
    """Django doesn't recommend using signals anymore, but we need to remove this cache entry
    and this is the only way to catch Query deletes and instance deletes."""
    logging.debug(f'[user_post_delete] Clearing allow list entry for {instance.email}')
    delete_cache_allow_list_entry(instance.email)


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(uuid=instance.uuid)
    except sender.DoesNotExist:
        return None

    if old_instance.email != instance.email:
        logging.debug(f'[user_pre_save] Clearing allow list entry for {old_instance.email}')
        delete_cache_allow_list_entry(old_instance.email)
