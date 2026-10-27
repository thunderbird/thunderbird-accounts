import json


def parse_contact_payload(request) -> dict:
    """Return the JSON payload posted in the multipart ``data`` field of the contact form.

    Raises ValueError when the field is not valid JSON or does not decode to an object."""
    raw = request.data.get('data', '{}')
    if isinstance(raw, dict):
        return raw

    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Contact form payload must be a JSON object')
    return payload
