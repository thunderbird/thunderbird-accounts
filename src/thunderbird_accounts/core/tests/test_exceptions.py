from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient


@api_view(['GET'])
@permission_classes([AllowAny])
def unexpected_error_view(request):
    raise RuntimeError('sensitive upstream details')


@api_view(['GET'])
@permission_classes([AllowAny])
def validation_error_view(request):
    raise ValidationError('Invalid request')


urlpatterns = [
    path('unexpected/', unexpected_error_view),
    path('validation/', validation_error_view),
]


@override_settings(ROOT_URLCONF=__name__)
class DrfExceptionHandlerTestCase(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=False)
    @patch('thunderbird_accounts.core.exceptions.logger.exception')
    def test_unexpected_exception_returns_generic_json_and_is_logged(self, mock_log_exception):
        response = self.client.get('/unexpected/', HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(response.json(), {'detail': 'Internal server error'})
        self.assertNotContains(response, 'sensitive upstream details', status_code=500)
        mock_log_exception.assert_called_once()

    @patch('thunderbird_accounts.core.exceptions.logger.exception')
    def test_known_drf_exception_keeps_standard_response(self, mock_log_exception):
        response = self.client.get('/validation/', HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ['Invalid request'])
        mock_log_exception.assert_not_called()

    @override_settings(DEBUG=True)
    @patch('thunderbird_accounts.core.exceptions.logger.exception')
    def test_development_response_includes_exception_detail(self, mock_log_exception):
        response = self.client.get('/unexpected/', HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'detail': 'sensitive upstream details'})
        mock_log_exception.assert_called_once()
