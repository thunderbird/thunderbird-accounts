"""Admin module. Anything with the user app in the admin panel is defined here."""

from django.contrib import admin
from django.contrib.admin.models import LogEntry

from thunderbird_accounts.authentication.admin.models import CustomUserAdmin, AllowListEntryAdmin, LogEntryAdmin
from thunderbird_accounts.authentication.models import User, AllowListEntry

# Register the User admin here
admin.site.register(User, CustomUserAdmin)
admin.site.register(AllowListEntry, AllowListEntryAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
