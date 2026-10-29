"""
Backward compatibility proxy module.
Core authentication logic has been moved to apps.authentication.authentication.
"""
from apps.authentication.authentication import (
    ACCOUNT_MODELS,
    AccountJWTAuthentication,
    AccountPrincipal,
    create_access_token,
    create_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
)

__all__ = [
    "ACCOUNT_MODELS",
    "AccountJWTAuthentication",
    "AccountPrincipal",
    "create_access_token",
    "create_token_pair",
    "revoke_refresh_token",
    "rotate_refresh_token",
]

try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class AccountJWTScheme(OpenApiAuthenticationExtension):
        target_class = "api.v1.authentication.AccountJWTAuthentication"
        name = "jwtAuth"

        def get_security_definition(self, auto_schema):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
except ImportError:
    pass