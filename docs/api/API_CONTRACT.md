# Getto Platform API Contract

API base path:

/api/v1/

The backend developer is responsible for maintaining
stable API contracts.

Every endpoint should document:

- HTTP method
- URL
- Authentication requirement
- Permissions
- Request parameters
- Request body
- Response body
- HTTP status codes
- Validation errors
- Error responses

Frontend developers should integrate with documented
API contracts rather than directly accessing PostgreSQL.
