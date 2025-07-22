from rest_framework import serializers
from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'uuid',
            'email',
            'display_name',
            'avatar_url',
            'timezone',
            'language',
            'last_login',
            'created_at',
            'updated_at',
        ]


class UserCacheSerializer(serializers.ModelSerializer):
    """
    Version 1
    Formats a user model to the json format below:
    {
        "_version": "1",
        "uuid": "7baaf446-d747-4b7c-ae87-1aab58a9fcd9",
        "username": "My Username",
        "display_name": "My Display Name",
        "full_name": "my full name",
        "email": "my@email.address",
        "oidc_id": "123abc",
        "language": "en",
        "avatar_url": "https://coolcatpics.local/cat.png",
        "timezone": "America/Vancouver",
        "date_joined": "2024-11-13T16:57:11.968Z",
        "last_login": "2024-11-13T16:57:11.968Z",
        "created_at": "2024-11-13T16:57:11.968Z",
        "updated_at": "2024-11-13T16:57:11.968Z",
        "access": ["apmt", "send", "assist"]
    }"""

    # Schema version
    _version = serializers.IntegerField(default=1, read_only=True)
    # This is hard-coded for now but it should be a user-level permission
    access = serializers.ListField(default=['appointment', 'assist', 'send'], read_only=True)
    full_name = serializers.SerializerMethodField(method_name='get_full_name', read_only=True)

    def get_full_name(self, instance: User):
        return ' '.join([instance.first_name, instance.last_name]).strip()

    class Meta:
        model = User
        fields = [
            # Schema-specific
            '_version',
            # General
            'uuid',
            'username',
            'display_name',
            'full_name',
            'email',
            'oidc_id',
            # Pref fields
            'language',
            'avatar_url',
            'timezone',
            # ACL
            'access',
            # Date fields
            'date_joined',
            'last_login',
            'created_at',
            'updated_at',
        ]
