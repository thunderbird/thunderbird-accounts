
## Patterns

### Guard against double-click to delete

Users may double-click on delete actions, causing the second request to return a resource not found error. On the backend, a delete action should not treat a "not found" condition as an error,
but should log at the info level and return non-found to the frontend.

## Security

- All plans and implementations must be developed and reviewed with security best practices in
mind, guarding against OWASP Top Ten other common vulnerabilities.

- Use DRF permission decorators for auth checks

## Keep views clean

`views.py` files should contain only route functions. Another internal or supporting functions
should be moved to another layer.

## Redirect when we can

If a route is renamed or moved, implement a redirect if there's one that make sense.

## Logging

- `logging.error()` gets sent to Sentry. If the intent is not to log an exception, use `warn` or `info` instead.

- Log strings should include a prefix that describes the part of the code the log came from.


