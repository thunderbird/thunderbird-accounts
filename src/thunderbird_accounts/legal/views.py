import sentry_sdk
from django.apps import apps
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
import json
import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from thunderbird_accounts.authentication.utils import delete_user_data
from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse


def _read_legal_content(content_path: str, locale: str) -> str:
    """Read pre-rendered HTML for a legal document.

    Unsupported locales use ``settings.DEFAULT_LANGUAGE``. If the requested
    locale file is missing but the default-language file exists in the same
    directory, that file is returned instead.
    """
    if locale not in settings.SUPPORTED_LEGAL_LANGUAGES:
        locale = settings.DEFAULT_LANGUAGE

    legal_templates_path = Path(apps.get_app_config('legal').path, 'templates')

    doc_path = Path(legal_templates_path, content_path, f'{locale}.html').resolve()
    default_path = Path(legal_templates_path, content_path, f'{settings.DEFAULT_LANGUAGE}.html').resolve()

    if not doc_path.is_relative_to(legal_templates_path) or not default_path.is_relative_to(
        legal_templates_path
    ):
        sentry_sdk.set_extra('doc_path', doc_path)
        sentry_sdk.set_extra('default_path', default_path)
        logging.error('directory traversal attack!')
        return ''

    try:
        return get_template(str(doc_path)).render()
    except TemplateDoesNotExist as ex:
        logging.error(f'Legal content file not found: {ex}. Looked for it in: {ex.tried}')
        return get_template(str(default_path)).render()


def _record_response(request, action: str) -> JsonResponse:
    """Record an accept or decline response for all current legal documents."""
    data = json.loads(request.body)
    source_context = data.get('source_context', '')

    current_docs = LegalDocument.objects.filter(is_current=True)

    created = []
    for doc in current_docs:
        response = LegalDocumentResponse.objects.create(
            user=request.user,
            document=doc,
            action=action,
            source_context=source_context,
        )
        created.append(
            {
                'document_type': doc.document_type,
                'version': doc.version,
                'action': response.action,
                'responded_at': response.created_at.isoformat(),
            }
        )

    return JsonResponse({'responses': created})


@login_required
@require_http_methods(['GET'])
def get_current_legal_docs(request):
    """Returns current TOS and Privacy documents with their pre-rendered HTML content
    and whether the authenticated user has accepted them."""
    current_docs = LegalDocument.objects.filter(is_current=True)
    locale = request.GET.get('locale', settings.DEFAULT_LANGUAGE)

    accepted_doc_ids = set()
    if request.user.is_authenticated:
        accepted_doc_ids = set(
            LegalDocumentResponse.objects.filter(
                user=request.user,
                document__in=current_docs,
                action=LegalDocumentResponse.Action.ACCEPTED,
            ).values_list('document_id', flat=True)
        )

    docs_data = []
    for doc in current_docs:
        docs_data.append(
            {
                'uuid': str(doc.uuid),
                'document_type': doc.document_type,
                'version': doc.version,
                'content': _read_legal_content(doc.content_path, locale),
                'accepted': doc.uuid in accepted_doc_ids,
            }
        )

    return JsonResponse({'documents': docs_data})


@login_required
@require_http_methods(['POST'])
def accept_legal_docs(request):
    return _record_response(request, LegalDocumentResponse.Action.ACCEPTED)


@login_required
@require_http_methods(['POST'])
def decline_legal_docs(request):
    _record_response(request, LegalDocumentResponse.Action.DECLINED)

    if not request.user.is_awaiting_payment_verification and not request.user.has_active_subscription:
        delete_user_data(request.user)
        django_logout(request)
        return JsonResponse({'redirect_url': '/'})

    # User has an active subscription!
    # Until we have a way to delete the user data across all services
    # We'll redirect them to the contact page with a message.
    messages.warning(request, _("We're sorry to see you go! Please contact support to cancel your account."))

    return JsonResponse({'redirect_url': '/contact'})
