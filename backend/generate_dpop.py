import jwt
import uuid
import time
import base64
from cryptography.hazmat.primitives import serialization

# Load private key
with open("dpop-private.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# Extract public key
public_key = private_key.public_key()
public_numbers = public_key.public_numbers()

# Convert x and y to base64url (NOT hex)
def b64url_uint(val):
    return base64.urlsafe_b64encode(val.to_bytes(32, "big")).rstrip(b"=").decode("ascii")

jwk = {
    "kty": "EC",
    "crv": "P-256",
    "x": b64url_uint(public_numbers.x),
    "y": b64url_uint(public_numbers.y)
}

# Build DPoP proof
token = jwt.encode(
    {
        "htu": "https://integrator-5266877.okta.com/oauth2/aus104bue06qKRHEC698/v1/token",
        "htm": "POST",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time())
    },
    private_key,
    algorithm="ES256",
    headers={
        "typ": "dpop+jwt",
        "jwk": jwk
    }
)

print(token)
