import hashlib
import hmac
import json


def create_webhook_hash(secret: str, payload: dict):
    """Creates a sha256 hash from a given payload and given webhook secret"""
    payload = json.dumps(payload).encode('utf-8')
    return hmac.new(secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
