
## Patterns

### Guard against double-click to delete

Users may double-click on delete actions, causing the second request to return a resource not found error. On the backend, a delete action should not treat a "not found" condition as an error,
but should log at the info level and return non-found to the frontend.

## Security

All plans and implementations must be developed and reviewed with security best practices in
mind, guarding against OWASP Top Ten other common vulnerabilities.
