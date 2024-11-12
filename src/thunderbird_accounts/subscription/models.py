from django.db import models

from thunderbird_accounts.authentication.models import User
from thunderbird_accounts.utils.models import BaseModel


class Customer(BaseModel):
    """A paddle customer.

    :param paddle_id: The customer id field in paddle
    :param name: The name of the customer
    :param email: The email of the customer
    """
    paddle_id = models.CharField(max_length=256)

    name = models.CharField(max_length=128)
    email = models.CharField(max_length=256)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
        ]

    def __str__(self):
        return f'Customer [{self.uuid}] {self.name}'


class Subscription(BaseModel):
    """A paddle subscription.

    :param name: The name of the subscription
    :param paddle_id: The subscription's paddle id
    :param is_active: Is this subscription active?
    :param active_since: Datetime when the subscription became active
    :param inactive_since: Datetime when the subscription became inactive
    """
    name = models.CharField(max_length=128)
    paddle_id = models.CharField(max_length=256)
    is_active = models.BooleanField()
    active_since = models.DateTimeField()
    inactive_since = models.DateTimeField()

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return f"Subscription [{self.uuid}] {self.name}"

    class Meta(BaseModel.Meta):
        indexes = [
            *BaseModel.Meta.indexes,
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['active_since']),
            models.Index(fields=['inactive_since']),
        ]
