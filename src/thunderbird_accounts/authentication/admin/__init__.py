"""Admin module. Anything with the user app in the admin panel is defined here."""
from django.contrib import admin

from thunderbird_accounts.authentication.admin.models import CustomUserAdmin
from thunderbird_accounts.authentication.models import User

# Register the User admin here
admin.site.register(User, CustomUserAdmin)
