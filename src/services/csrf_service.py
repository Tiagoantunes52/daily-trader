"""CSRF protection service for state-changing endpoints."""

import hashlib
import hmac
import secrets
import time

from src.utils.config import config


class CSRFService:
    """Service for CSRF token generation and validation."""

    def __init__(self, token_lifetime: int = 3600):
        """
        Initialize CSRF service.

        Args:
            token_lifetime: Token lifetime in seconds (default: 1 hour)
        """
        self.token_lifetime = token_lifetime
        self.secret_key = config.jwt.secret_key.encode()

    def generate_token(self, session_id: str | None = None) -> str:
        """
        Generate a CSRF token.

        Args:
            session_id: Optional session identifier for additional security

        Returns:
            Base64-encoded CSRF token
        """
        # Generate random token data
        random_data = secrets.token_bytes(32)
        timestamp = str(int(time.time())).encode()

        # Include session ID if provided with delimiter
        if session_id:
            session_data = b"|" + session_id.encode()
        else:
            session_data = b""

        # Create token payload
        payload = random_data + timestamp + session_data

        # Create HMAC signature
        signature = hmac.new(self.secret_key, payload, hashlib.sha256).digest()

        # Combine payload and signature
        token_data = payload + signature

        # Return base64-encoded token
        import base64

        return base64.b64encode(token_data).decode()

    def validate_token(self, token: str, session_id: str | None = None) -> bool:
        """
        Validate a CSRF token.

        Args:
            token: The CSRF token to validate
            session_id: Optional session identifier for additional security

        Returns:
            True if token is valid, False otherwise
        """
        try:
            import base64

            # Decode token
            token_data = base64.b64decode(token.encode())

            # Extract components
            if len(token_data) < 72:  # 32 (random) + 10 (timestamp) + 32 (signature) minimum
                return False

            # Extract signature (last 32 bytes)
            signature = token_data[-32:]
            payload = token_data[:-32]

            # Extract timestamp and session data
            remaining = payload[32:]

            # Find delimiter to separate timestamp from session data
            delimiter_pos = remaining.find(b"|")

            if delimiter_pos == -1:
                # No session data
                timestamp_bytes = remaining
                session_data = b""
            else:
                # Session data present
                timestamp_bytes = remaining[:delimiter_pos]
                session_data = remaining[delimiter_pos + 1 :]  # Skip the delimiter

            # Parse timestamp
            try:
                timestamp_str = timestamp_bytes.decode()
                timestamp = int(timestamp_str)
            except (ValueError, UnicodeDecodeError):
                return False

            # Check if session ID matches
            if session_id:
                expected_session_data = session_id.encode()
                if session_data != expected_session_data:
                    return False
            elif session_data:
                # Token has session data but none expected
                return False

            # Verify signature
            expected_signature = hmac.new(self.secret_key, payload, hashlib.sha256).digest()

            if not hmac.compare_digest(signature, expected_signature):
                return False

            # Check token expiration
            current_time = int(time.time())
            if current_time - timestamp > self.token_lifetime:
                return False

            return True

        except (ValueError, TypeError, UnicodeDecodeError):
            return False

    def get_token_header_name(self) -> str:
        """
        Get the header name for CSRF tokens.

        Returns:
            The header name to use for CSRF tokens
        """
        return "X-CSRF-Token"
