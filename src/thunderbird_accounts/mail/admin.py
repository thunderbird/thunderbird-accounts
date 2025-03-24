from django.contrib import admin

from thunderbird_accounts.mail.models import Account, GroupMember, Email


class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 1


class EmailInline(admin.TabularInline):
    model = Email
    extra = 1


class AccountAdmin(admin.ModelAdmin):
    inlines = (
        GroupMemberInline,
        EmailInline,
    )


# Register your models here.
admin.site.register(Account, AccountAdmin)
admin.site.register(GroupMember)
admin.site.register(Email)
