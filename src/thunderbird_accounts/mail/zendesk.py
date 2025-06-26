import requests
import mimetypes
from django.conf import settings


class ZendeskClient(object):
    """Client to connect to Zendesk API."""

    def __init__(self, **kwargs):
        """Initialize Zendesk API client."""
        self.email = settings.ZENDESK_USER_EMAIL
        self.token = settings.ZENDESK_API_TOKEN
        self.subdomain = settings.ZENDESK_SUBDOMAIN
        self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"


    def create_ticket(self, ticket_fields):
        """Create a ticket in Zendesk using the Requests API."""
        url = f"{self.base_url}/requests.json"
        comment = {
            "body": ticket_fields.get("description", ""),
        }

        # Add upload tokens if attachments are provided
        attachments = ticket_fields.get("attachments", [])
        if attachments:
            upload_tokens = []
            for attachment in attachments:
                token = attachment.get('token')
                if token:
                    upload_tokens.append(token)

            if upload_tokens:
                comment["uploads"] = upload_tokens

        payload = {
            "request": {
                "subject": ticket_fields.get("subject"),
                "comment": comment,
                "requester": {
                    "name": "Accounts Support",
                    "email": ticket_fields.get("email")
                },
                "custom_fields": [
                    {
                        "id": settings.ZENDESK_PRODUCT_FIELD_ID,
                        "value": ticket_fields.get("product")
                    },
                    {
                        "id": settings.ZENDESK_TYPE_OF_REQUEST_FIELD_ID,
                        "value": ticket_fields.get("ticket_type")
                    }
                ]
            }
        }

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            auth=(f'{self.email}/token', self.token),
            json=payload
        )

        return response


    def upload_file(self, uploaded_file):
        """Upload a file to Zendesk and return the upload token."""
        url = f"{self.base_url}/uploads.json"

        content_type, _ = mimetypes.guess_type(uploaded_file.name)
        if not content_type:
            content_type = 'application/binary'

        response = requests.post(
            url,
            auth=(f'{self.email}/token', self.token),
            headers={"Content-Type": content_type},
            data=uploaded_file.read(),
            params={'filename': uploaded_file.name}
        )

        if response.status_code == 201:
            data = response.json()
            upload_data = data.get('upload', {})
            upload_token = upload_data.get('token')

            # Get filename from the attachment data
            attachment = upload_data.get('attachment', {})
            filename = attachment.get('file_name', uploaded_file.name)

            return {
                'success': True,
                'upload_token': upload_token,
                'filename': filename
            }
        else:
            return {
                'success': False,
                'error': 'Zendesk upload failed',
                'details': response.text
            }
