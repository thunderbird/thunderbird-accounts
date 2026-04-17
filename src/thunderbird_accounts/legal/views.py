import json
import logging
from pathlib import Path

import sentry_sdk
from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from thunderbird_accounts.legal.models import LegalDocument, LegalDocumentResponse


def _read_legal_content(content_path: str, locale: str) -> str:
    """Read pre-rendered HTML content for a legal document, falling back to English."""
    # locale comes as a user defined query param, so getting only the file name
    # and discarding the path to avoid path traversal attacks
    safe_locale = Path(locale).name
    content_dir = Path(settings.ASSETS_ROOT, 'legal', content_path)
    content_file = content_dir / f'{safe_locale}.html'

    if not content_file.exists():
        content_file = content_dir / f'{settings.DEFAULT_LANGUAGE}.html'

    if not content_file.exists():
        logging.error(f'Legal content file not found: {content_file}')
        return ''

    resolved = content_file.resolve()
    if not resolved.is_relative_to(Path(settings.ASSETS_ROOT).resolve()):
        logging.error(f'Legal content path escapes assets root: {content_file}')
        return ''

    return resolved.read_text(encoding='utf-8')


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
        created.append({
            'document_type': doc.document_type,
            'version': doc.version,
            'action': response.action,
            'responded_at': response.created_at.isoformat(),
        })

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
        docs_data.append({
            'uuid': str(doc.uuid),
            'document_type': doc.document_type,
            'version': doc.version,
            'content': _read_legal_content(doc.content_path, locale),
            'accepted': doc.uuid in accepted_doc_ids,
        })

    return JsonResponse({'documents': docs_data})


@login_required
@require_http_methods(['POST'])
def accept_legal_docs(request):
    return _record_response(request, LegalDocumentResponse.Action.ACCEPTED)


@login_required
@require_http_methods(['POST'])
def decline_legal_docs(request):
    _record_response(request, LegalDocumentResponse.Action.DECLINED)

    # TODO: Offboard the user / Delete user data (?)

    if settings.AUTH_SCHEME == 'oidc' and request.user.oidc_id:
        try:
            from thunderbird_accounts.authentication.clients import KeycloakClient, RequestMethods

            kc_client = KeycloakClient()
            kc_client.request(f'users/{request.user.oidc_id}/logout', RequestMethods.POST)
        except Exception as ex:
            logging.error('Failed to logout Keycloak session', ex)
            sentry_sdk.capture_exception(ex)

    django_logout(request)

    return JsonResponse({'redirect_url': '/'})
