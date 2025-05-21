class UnexpectedBehaviour(Exception):
    """Raise when something weird happens,
    you should call sentry_sdk.set_context to give some context to the error"""

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return f'Unexpected Behaviour: {self.message}'
