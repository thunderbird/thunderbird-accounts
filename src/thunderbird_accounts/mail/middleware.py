from django.http import HttpRequest
from thunderbird_accounts.authentication.tokens import AccessTokenPolicy, get_user_access_token
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
        user = request.user

        # If the user exists, has a stalwart account reference and an oidc access token
        # Check if we need to fix their archives folder, and do it if we need to.
        if user and user.account_set.count() > 0:
            archive_folders_to_check = user.account_set.filter(verified_archive_folder=False)
            for account in archive_folders_to_check:
                oidc_access_token = get_user_access_token(
                    request,
                    policy=AccessTokenPolicy.REQUIRE_KNOWN_FRESH,
                )
                if not oidc_access_token:
                    return

                fix_archives_folder(
                    oidc_access_token,
                    account,
                    refresh_access_token=lambda: get_user_access_token(request, policy=AccessTokenPolicy.FORCE_REFRESH),
                )
