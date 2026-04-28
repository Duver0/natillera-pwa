"""
Shared helpers for generating RSA key pairs and signed JWTs in middleware tests.
"""
import json
import time
from typing import Tuple, Dict, Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm


TEST_KID = "test-key-id"
TEST_USER_ID = "user-test-uuid-1234"
TEST_SUPABASE_URL = "https://test.supabase.co"
TEST_ISSUER = f"{TEST_SUPABASE_URL}/auth/v1"


def generate_rsa_key_pair():
    """Generate RSA key pair for test JWT signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    return private_key, private_key.public_key()


def public_key_to_jwk(public_key, kid: str = TEST_KID) -> Dict[str, Any]:
    """Convert RSA public key to JWK dict."""
    jwk_str = RSAAlgorithm.to_jwk(public_key)
    jwk = json.loads(jwk_str)
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return jwk


def make_valid_token(private_key, user_id: str = TEST_USER_ID, kid: str = TEST_KID) -> str:
    """Create a valid, non-expired RS256 JWT."""
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iss": TEST_ISSUER,
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "role": "authenticated",
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def make_expired_token(private_key, user_id: str = TEST_USER_ID, kid: str = TEST_KID) -> str:
    """Create an RS256 JWT that is already expired."""
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iss": TEST_ISSUER,
        "exp": int(time.time()) - 3600,
        "iat": int(time.time()) - 7200,
        "role": "authenticated",
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )
