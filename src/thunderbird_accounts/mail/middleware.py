from django.http import HttpRequest
from thunderbird_accounts.mail.utils import fix_archives_folder


class FixMissingArchivesFolderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.has_active_subscription:
            # This needs to be here for after they subscribe
            # we need their oidc access token which is only available on the request...
            self.check_if_we_need_to_fix_archives_folder(request)

        return self.get_response(request)

    def check_if_we_need_to_fix_archives_folder(self, request: HttpRequest):
        oidc_access_token = request.session['oidc_access_token']
        user = request.user

        # If the user exists, has a stalwart account reference and an oidc access token
        # Check if we need to fix their archives folder, and do it if we need to.
        if user and user.account_set.count() > 0 and oidc_access_token:
            archive_folders_to_check = user.account_set.filter(verified_archive_folder=False)
            for account in archive_folders_to_check:
                fix_archives_folder(oidc_access_token, account)
