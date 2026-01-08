"""Authentication service for user registration, login, and logout."""

from sqlalchemy.orm import Session

from src.database.models import OAuthConnection, User
from src.models.auth_schemas import TokenResponse
from src.services.auth_user_service import AuthUserService
from src.services.encryption_service import EncryptionService
from src.services.oauth_service import OAuthService
from src.services.password_service import PasswordService
from src.services.token_service import TokenService
from src.utils.config import config


class AuthenticationService:
    """Service for handling user authentication operations."""

    def __init__(self, db_session: Session):
        """
        Initialize authentication service with database session.

        Args:
            db_session: SQLAlchemy database session
        """
        if not db_session:
            raise ValueError("Database session is required")

        self.db_session = db_session
        self.user_service = AuthUserService(db_session)
        self.password_service = PasswordService()
        self.token_service = TokenService()
        self.oauth_service = OAuthService()
        self.encryption_service = EncryptionService(config.encryption.encryption_key)

    def register(self, email: str, password: str, name: str) -> User:
        """
        Register a new user with email and password.

        Args:
            email: User email address
            password: Plaintext password
            name: User's display name

        Returns:
            Created User object

        Raises:
            ValueError: If validation fails or email already exists
        """
        # Validate email format (basic validation)
        if not email or "@" not in email:
            raise ValueError("Invalid email format")

        # Normalize email
        email = email.lower().strip()

        # Validate password strength
        is_valid, errors = self.password_service.validate_password_strength(password)
        if not is_valid:
            raise ValueError(f"Password validation failed: {', '.join(errors)}")

        # Validate name
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        # Check if email already exists
        if self.user_service.user_exists(email):
            raise ValueError(f"Email already registered: {email}")

        # Hash password
        password_hash = self.password_service.hash_password(password)

        # Create user
        user = self.user_service.create_user(
            email=email, password_hash=password_hash, name=name.strip()
        )

        return user

    def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate user with email and password.

        Args:
            email: User email address
            password: Plaintext password

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            ValueError: If credentials are invalid (generic error message)
        """
        # Normalize email
        email = email.lower().strip()

        # Retrieve user by email
        user = self.user_service.get_user_by_email(email)

        # Generic error message for security (don't reveal which field is wrong)
        generic_error = "Invalid email or password"

        if not user:
            raise ValueError(generic_error)

        # Verify password
        if not user.password_hash:
            # OAuth-only user trying to login with password
            raise ValueError(generic_error)

        is_valid = self.password_service.verify_password(password, user.password_hash)
        if not is_valid:
            raise ValueError(generic_error)

        # Generate tokens
        access_token = self.token_service.create_access_token(user.id)
        refresh_token = self.token_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    def logout(self, user_id: int) -> None:
        """
        Logout user by invalidating their session.

        Note: In a stateless JWT implementation, logout is typically handled
        client-side by removing tokens. This method is a placeholder for
        future token blacklisting or session management.

        Args:
            user_id: User ID to logout

        Raises:
            ValueError: If user_id is invalid
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("User ID must be a positive integer")

        # Verify user exists
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # In a stateless JWT system, logout is handled client-side
        # Future enhancement: implement token blacklist or session invalidation

    async def handle_google_callback(self, code: str, state: str) -> TokenResponse:
        """
        Handle Google OAuth callback and create/login user.

        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            ValueError: If OAuth flow fails or code is invalid
        """
        if not code:
            raise ValueError("Authorization code is required")

        # Exchange code for access token and user info
        oauth_data = await self.oauth_service.exchange_google_code(code)

        # Extract user info
        user_info = oauth_data["user_info"]
        provider_user_id = user_info["provider_user_id"]
        email = user_info["email"]
        name = user_info["name"]

        if not email:
            raise ValueError("Email not provided by Google")

        # Normalize email
        email = email.lower().strip()

        # Check if OAuth connection already exists
        existing_connection = (
            self.db_session.query(OAuthConnection)
            .filter(
                OAuthConnection.provider == "google",
                OAuthConnection.provider_user_id == provider_user_id,
            )
            .first()
        )

        if existing_connection:
            # User already exists with this OAuth connection
            user = existing_connection.user

            # Update OAuth tokens (encrypt before storing)
            existing_connection.access_token = self.encryption_service.encrypt(
                oauth_data["access_token"]
            )
            if oauth_data.get("refresh_token"):
                existing_connection.refresh_token = self.encryption_service.encrypt(
                    oauth_data["refresh_token"]
                )
            self.db_session.commit()
        else:
            # Check if user exists by email
            user = self.user_service.get_user_by_email(email)

            if user:
                # User exists, add OAuth connection
                oauth_connection = OAuthConnection(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=provider_user_id,
                    access_token=self.encryption_service.encrypt(oauth_data["access_token"]),
                    refresh_token=self.encryption_service.encrypt(oauth_data["refresh_token"])
                    if oauth_data.get("refresh_token")
                    else None,
                )
                self.db_session.add(oauth_connection)
                self.db_session.commit()
            else:
                # Create new user with OAuth connection
                user = User(
                    email=email,
                    name=name or "Google User",
                    password_hash=None,  # OAuth-only user
                    is_email_verified=True,  # Email verified by Google
                )
                self.db_session.add(user)
                self.db_session.flush()  # Get user ID

                oauth_connection = OAuthConnection(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=provider_user_id,
                    access_token=self.encryption_service.encrypt(oauth_data["access_token"]),
                    refresh_token=self.encryption_service.encrypt(oauth_data["refresh_token"])
                    if oauth_data.get("refresh_token")
                    else None,
                )
                self.db_session.add(oauth_connection)
                self.db_session.commit()

        # Generate JWT tokens
        access_token = self.token_service.create_access_token(user.id)
        refresh_token = self.token_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    async def handle_github_callback(self, code: str, state: str) -> TokenResponse:
        """
        Handle GitHub OAuth callback and create/login user.

        Args:
            code: Authorization code from GitHub
            state: State parameter for CSRF protection

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            ValueError: If OAuth flow fails or code is invalid
        """
        if not code:
            raise ValueError("Authorization code is required")

        # Exchange code for access token and user info
        oauth_data = await self.oauth_service.exchange_github_code(code)

        # Extract user info
        user_info = oauth_data["user_info"]
        provider_user_id = user_info["provider_user_id"]
        email = user_info["email"]
        name = user_info["name"]

        if not email:
            raise ValueError("Email not provided by GitHub")

        # Normalize email
        email = email.lower().strip()

        # Check if OAuth connection already exists
        existing_connection = (
            self.db_session.query(OAuthConnection)
            .filter(
                OAuthConnection.provider == "github",
                OAuthConnection.provider_user_id == provider_user_id,
            )
            .first()
        )

        if existing_connection:
            # User already exists with this OAuth connection
            user = existing_connection.user

            # Update OAuth tokens (encrypt before storing)
            existing_connection.access_token = self.encryption_service.encrypt(
                oauth_data["access_token"]
            )
            if oauth_data.get("refresh_token"):
                existing_connection.refresh_token = self.encryption_service.encrypt(
                    oauth_data["refresh_token"]
                )
            self.db_session.commit()
        else:
            # Check if user exists by email
            user = self.user_service.get_user_by_email(email)

            if user:
                # User exists, add OAuth connection
                oauth_connection = OAuthConnection(
                    user_id=user.id,
                    provider="github",
                    provider_user_id=provider_user_id,
                    access_token=self.encryption_service.encrypt(oauth_data["access_token"]),
                    refresh_token=self.encryption_service.encrypt(oauth_data["refresh_token"])
                    if oauth_data.get("refresh_token")
                    else None,
                )
                self.db_session.add(oauth_connection)
                self.db_session.commit()
            else:
                # Create new user with OAuth connection
                user = User(
                    email=email,
                    name=name or "GitHub User",
                    password_hash=None,  # OAuth-only user
                    is_email_verified=True,  # Email verified by GitHub
                )
                self.db_session.add(user)
                self.db_session.flush()  # Get user ID

                oauth_connection = OAuthConnection(
                    user_id=user.id,
                    provider="github",
                    provider_user_id=provider_user_id,
                    access_token=self.encryption_service.encrypt(oauth_data["access_token"]),
                    refresh_token=self.encryption_service.encrypt(oauth_data["refresh_token"])
                    if oauth_data.get("refresh_token")
                    else None,
                )
                self.db_session.add(oauth_connection)
                self.db_session.commit()

        # Generate JWT tokens
        access_token = self.token_service.create_access_token(user.id)
        refresh_token = self.token_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    def get_decrypted_oauth_token(self, oauth_connection: OAuthConnection) -> dict[str, str | None]:
        """
        Get decrypted OAuth tokens from a connection.

        Args:
            oauth_connection: OAuthConnection object with encrypted tokens

        Returns:
            Dictionary with decrypted access_token and refresh_token

        Raises:
            ValueError: If decryption fails
        """
        if not oauth_connection:
            raise ValueError("OAuth connection is required")

        result = {}

        if oauth_connection.access_token:
            try:
                result["access_token"] = self.encryption_service.decrypt(
                    oauth_connection.access_token
                )
            except Exception as e:
                raise ValueError(f"Failed to decrypt access token: {e}") from e
        else:
            result["access_token"] = None

        if oauth_connection.refresh_token:
            try:
                result["refresh_token"] = self.encryption_service.decrypt(
                    oauth_connection.refresh_token
                )
            except Exception as e:
                raise ValueError(f"Failed to decrypt refresh token: {e}") from e
        else:
            result["refresh_token"] = None

        return result
