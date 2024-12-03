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
