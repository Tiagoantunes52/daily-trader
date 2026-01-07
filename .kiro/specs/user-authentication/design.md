# Design Document: User Authentication with OAuth

## Overview

This design implements a comprehensive authentication system for the Daily Market Tips application using JWT tokens and OAuth2 providers (Google, GitHub). The system provides both local authentication (email/password) and federated authentication through OAuth providers. The architecture separates concerns into authentication service, user service, and token management layers, with frontend login UI and protected API endpoints.

## Architecture

The authentication system follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Login Page | OAuth Redirect Handler | Dashboard    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Authentication Routes (login, register, oauth)     │   │
│  │  ├─ POST /auth/register                             │   │
│  │  ├─ POST /auth/login                                │   │
│  │  ├─ POST /auth/refresh                              │   │
│  │  ├─ POST /auth/logout                               │   │
│  │  ├─ GET /auth/google/authorize                      │   │
│  │  ├─ GET /auth/google/callback                       │   │
│  │  ├─ GET /auth/github/authorize                      │   │
│  │  └─ GET /auth/github/callback                       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Protected Routes (require JWT token)               │   │
│  │  ├─ GET /api/user/profile                           │   │
│  │  ├─ PUT /api/user/profile                           │   │
│  │  ├─ POST /api/user/change-password                  │   │
│  │  └─ DELETE /api/user/account                        │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Authentication Service Layer                       │   │
│  │  ├─ AuthenticationService (login, register, oauth)  │   │
│  │  ├─ TokenService (JWT generation, validation)       │   │
│  │  ├─ PasswordService (hashing, validation)           │   │
│  │  └─ OAuthService (Google, GitHub integration)       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  User Service Layer                                 │   │
│  │  ├─ UserService (CRUD operations)                   │   │
│  │  └─ UserRepository (database access)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Database (SQLAlchemy)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  User Table                                          │   │
│  │  ├─ id (primary key)                                │   │
│  │  ├─ email (unique)                                  │   │
│  │  ├─ password_hash (nullable for OAuth-only users)   │   │
│  │  ├─ name                                            │   │
│  │  ├─ created_at                                      │   │
│  │  ├─ updated_at                                      │   │
│  │  └─ is_email_verified                               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  OAuthConnection Table                              │   │
│  │  ├─ id (primary key)                                │   │
│  │  ├─ user_id (foreign key)                           │   │
│  │  ├─ provider (google, github)                       │   │
│  │  ├─ provider_user_id                                │   │
│  │  ├─ access_token (encrypted)                        │   │
│  │  ├─ refresh_token (encrypted)                       │   │
│  │  └─ created_at                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Authentication Routes (FastAPI)

**File:** `src/api/auth_routes.py`

```python
# POST /auth/register
# Request: {email, password, name}
# Response: {user_id, email, message}
# Errors: 400 (validation), 409 (email exists)

# POST /auth/login
# Request: {email, password}
# Response: {access_token, refresh_token, user}
# Errors: 401 (invalid credentials), 400 (validation)

# POST /auth/refresh
# Request: {refresh_token}
# Response: {access_token}
# Errors: 401 (invalid/expired token)

# POST /auth/logout
# Request: {}
# Response: {message}
# Errors: 401 (not authenticated)

# GET /auth/google/authorize
# Redirects to Google OAuth consent screen

# GET /auth/google/callback
# Query params: code, state
# Response: Redirect to frontend with tokens

# GET /auth/github/authorize
# Redirects to GitHub OAuth authorization endpoint

# GET /auth/github/callback
# Query params: code, state
# Response: Redirect to frontend with tokens
```

### 2. User Routes (FastAPI)

**File:** `src/api/user_routes.py`

```python
# GET /api/user/profile
# Headers: Authorization: Bearer {access_token}
# Response: {id, email, name, auth_method, oauth_providers}
# Errors: 401 (unauthorized)

# PUT /api/user/profile
# Headers: Authorization: Bearer {access_token}
# Request: {name, email}
# Response: {id, email, name}
# Errors: 401 (unauthorized), 409 (email exists)

# POST /api/user/change-password
# Headers: Authorization: Bearer {access_token}
# Request: {current_password, new_password}
# Response: {message}
# Errors: 401 (unauthorized), 400 (validation)

# DELETE /api/user/account
# Headers: Authorization: Bearer {access_token}
# Response: {message}
# Errors: 401 (unauthorized)
```

### 3. Authentication Service

**File:** `src/services/authentication_service.py`

Handles user registration, login, and OAuth flows:

```python
class AuthenticationService:
    async def register(email: str, password: str, name: str) -> User
    async def login(email: str, password: str) -> TokenPair
    async def refresh_token(refresh_token: str) -> str
    async def logout(user_id: int) -> None
    async def handle_google_callback(code: str, state: str) -> TokenPair
    async def handle_github_callback(code: str, state: str) -> TokenPair
```

### 4. Token Service

**File:** `src/services/token_service.py`

Manages JWT token generation and validation:

```python
class TokenService:
    def create_access_token(user_id: int, expires_delta: timedelta) -> str
    def create_refresh_token(user_id: int, expires_delta: timedelta) -> str
    def verify_token(token: str) -> dict
    def decode_token(token: str) -> dict
```

### 5. Password Service

**File:** `src/services/password_service.py`

Handles password hashing and validation:

```python
class PasswordService:
    def hash_password(password: str) -> str
    def verify_password(password: str, hash: str) -> bool
    def validate_password_strength(password: str) -> bool
```

### 6. OAuth Service

**File:** `src/services/oauth_service.py`

Manages OAuth provider integrations:

```python
class OAuthService:
    async def get_google_authorization_url(state: str) -> str
    async def exchange_google_code(code: str) -> dict
    async def get_github_authorization_url(state: str) -> str
    async def exchange_github_code(code: str) -> dict
```

### 7. User Service

**File:** `src/services/user_service.py`

Manages user CRUD operations:

```python
class UserService:
    async def create_user(email: str, password_hash: str, name: str) -> User
    async def get_user_by_email(email: str) -> User
    async def get_user_by_id(user_id: int) -> User
    async def update_user(user_id: int, **kwargs) -> User
    async def delete_user(user_id: int) -> None
    async def user_exists(email: str) -> bool
```

### 8. Login Page Component (React)

**File:** `frontend/src/pages/LoginPage.jsx`

Features:
- Email and password input fields
- Google OAuth button
- GitHub OAuth button
- Error message display
- Loading state during authentication
- Form validation
- Redirect to dashboard on success

## Data Models

### User Model

```python
class User(Base):
    __tablename__ = "users"
    
    id: int = Column(Integer, primary_key=True)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    name: str = Column(String(255), nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_email_verified: bool = Column(Boolean, default=False)
    
    oauth_connections: List[OAuthConnection] = relationship("OAuthConnection", back_populates="user")
```

### OAuthConnection Model

```python
class OAuthConnection(Base):
    __tablename__ = "oauth_connections"
    
    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider: str = Column(String(50), nullable=False)  # 'google' or 'github'
    provider_user_id: str = Column(String(255), nullable=False)
    access_token: str = Column(String(1024), nullable=True)  # Encrypted
    refresh_token: str = Column(String(1024), nullable=True)  # Encrypted
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    user: User = relationship("User", back_populates="oauth_connections")
```

### Pydantic Schemas

```python
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    oauth_providers: List[str]
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Password Hash Consistency

*For any* valid password and its hash, verifying the password against the hash should always return true, and verifying an incorrect password should always return false.

**Validates: Requirements 2.1, 9.1**

### Property 2: Token Round-Trip Consistency

*For any* valid user ID, creating a token and then decoding it should produce the same user ID and token type.

**Validates: Requirements 5.1, 5.3**

### Property 3: Access Token Expiration

*For any* access token, if the current time is after the token's expiration time, token verification should fail with an expiration error.

**Validates: Requirements 5.2**

### Property 4: Refresh Token Validity

*For any* valid refresh token, exchanging it for a new access token should produce a valid access token with the same user ID.

**Validates: Requirements 5.3, 5.4**

### Property 5: Protected Endpoint Authorization

*For any* protected endpoint and any request without a valid token, the endpoint should return 401 Unauthorized status.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 6: Authenticated Request Processing

*For any* protected endpoint and any request with a valid token, the endpoint should process the request and extract the correct user information from the token.

**Validates: Requirements 6.4, 6.5**

### Property 7: OAuth User Creation Idempotence

*For any* OAuth provider and user profile, calling the OAuth callback handler multiple times with the same provider user ID should result in a single user record (no duplicates).

**Validates: Requirements 3.4, 4.4**

### Property 8: Session Invalidation on Logout

*For any* user session, after logout is called, subsequent requests using the same tokens should be rejected with 401 Unauthorized.

**Validates: Requirements 5.5**

### Property 9: Email Uniqueness Enforcement

*For any* email address, attempting to register two different users with the same email should fail on the second attempt with a conflict error.

**Validates: Requirements 1.2**

### Property 10: Password Strength Validation

*For any* password that fails strength validation, registration should be rejected with a validation error.

**Validates: Requirements 1.4**

### Property 11: Login Credential Verification

*For any* registered user, logging in with the correct password should succeed and return valid tokens, while logging in with an incorrect password should fail with a generic error.

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 12: Registration Email Validation

*For any* registration attempt, the system should validate email format and reject invalid email addresses.

**Validates: Requirements 1.1**

### Property 13: User Profile Retrieval

*For any* authenticated user, requesting their profile should return all required fields (email, name, authentication method) and only their own data.

**Validates: Requirements 8.1**

### Property 14: Profile Update Persistence

*For any* user profile update, the changes should be validated and persisted to the database, and subsequent profile retrievals should reflect the updates.

**Validates: Requirements 8.2**

### Property 15: Password Change Validation

*For any* password change request, the new password should be validated for strength, and the old password hash should be replaced with the new one.

**Validates: Requirements 8.3**

### Property 16: OAuth Disconnection Preservation

*For any* user with multiple OAuth connections, disconnecting one provider should remove only that connection while preserving the user account and other connections.

**Validates: Requirements 8.4**

### Property 17: Account Deletion Completeness

*For any* deleted user account, all associated user data and OAuth connections should be removed from the database.

**Validates: Requirements 8.5**

### Property 18: Bcrypt Hashing Algorithm

*For any* password stored in the system, the hash should be created using bcrypt with a cost factor of at least 12.

**Validates: Requirements 9.1**

### Property 19: Password Reset Token Expiration

*For any* expired password reset token, attempting to use it should fail with an expiration error.

**Validates: Requirements 9.3**

### Property 20: Session Invalidation on Password Reset

*For any* user who resets their password, all existing access and refresh tokens should be invalidated.

**Validates: Requirements 9.4**

### Property 21: OAuth Token Encryption

*For any* OAuth token stored in the database, it should be encrypted and not readable as plaintext.

**Validates: Requirements 9.5**

### Property 22: CSRF Token Validation

*For any* state-changing API request without a valid CSRF token, the request should be rejected.

**Validates: Requirements 9.6**

### Property 23: Registration Validation Error Messages

*For any* registration attempt with invalid data, the system should return specific error messages for each invalid field.

**Validates: Requirements 10.1**

### Property 24: Login Generic Error Messages

*For any* failed login attempt, the system should return a generic error message that does not reveal whether the email or password is incorrect.

**Validates: Requirements 10.2**

## Error Handling

### Authentication Errors

- **400 Bad Request**: Invalid input format, missing required fields, validation failures
- **401 Unauthorized**: Invalid credentials, expired tokens, missing authentication
- **409 Conflict**: Email already registered, duplicate OAuth connection
- **500 Internal Server Error**: Unexpected server errors, database failures

### Error Response Format

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "specific error for field"
  }
}
```

### Specific Error Codes

- `INVALID_CREDENTIALS`: Email or password incorrect
- `EMAIL_EXISTS`: Email already registered
- `WEAK_PASSWORD`: Password does not meet strength requirements
- `INVALID_TOKEN`: Token is malformed or invalid
- `TOKEN_EXPIRED`: Token has expired
- `OAUTH_ERROR`: OAuth provider returned an error
- `USER_NOT_FOUND`: User does not exist

## Testing Strategy

### Unit Tests

Unit tests verify specific examples and edge cases:

- Password hashing and verification with various inputs
- Token creation and decoding with different payloads
- Email validation and uniqueness checks
- Password strength validation with weak/strong passwords
- User registration with valid/invalid inputs
- Login with correct/incorrect credentials
- OAuth connection creation and retrieval

### Property-Based Tests

Property-based tests verify universal properties across all inputs:

- **Property 1**: Password hash consistency across all passwords
- **Property 2**: Token round-trip consistency for all user IDs
- **Property 3**: Access token expiration for all timestamps
- **Property 4**: Refresh token validity for all valid tokens
- **Property 5**: Protected endpoint authorization for all requests without tokens
- **Property 6**: Authenticated request processing for all valid tokens
- **Property 7**: OAuth user creation idempotence for all OAuth profiles
- **Property 8**: Session invalidation on logout for all user sessions
- **Property 9**: Email uniqueness enforcement for all email addresses
- **Property 10**: Password strength validation for all passwords

### Testing Configuration

- Minimum 100 iterations per property test
- Each property test tagged with feature name and property number
- Tag format: `Feature: user-authentication, Property {number}: {property_text}`
- Unit tests co-located with source files using `.test.py` suffix
- Both unit and property tests required for comprehensive coverage

## Security Considerations

1. **Password Storage**: Use bcrypt with minimum 12 rounds for hashing
2. **Token Security**: Store tokens in HTTP-only cookies, never in localStorage
3. **HTTPS Only**: All authentication endpoints require HTTPS
4. **CSRF Protection**: Implement CSRF tokens for state-changing operations
5. **OAuth State Parameter**: Use cryptographically secure random state for OAuth flows
6. **Token Expiration**: Access tokens expire in 15 minutes, refresh tokens in 7 days
7. **Sensitive Data**: Encrypt OAuth tokens at rest in database
8. **Rate Limiting**: Implement rate limiting on authentication endpoints
9. **Input Validation**: Validate all inputs on both frontend and backend
10. **Error Messages**: Generic error messages for login failures (don't reveal which field is wrong)

## Configuration

Environment variables required:

```
# JWT Configuration
JWT_SECRET_KEY=<secure-random-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# GitHub OAuth
GITHUB_CLIENT_ID=<github-client-id>
GITHUB_CLIENT_SECRET=<github-client-secret>
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback

# Email Configuration (for verification emails)
SMTP_SERVER=<smtp-server>
SMTP_PORT=587
SMTP_USERNAME=<email>
SMTP_PASSWORD=<password>
```
