# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require Bearer token authentication except `/auth/login` and `/auth/register`.

```http
Authorization: Bearer <token>
```

## Endpoints

### Authentication

#### POST /auth/register
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "phone": "+1234567890"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "end_user",
  "is_active": true,
  "created_at": "2026-02-08T10:00:00"
}
```

#### POST /auth/login
Login with credentials.

**Request:**
```http
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {...}
}
```

### Keystroke Dynamics

#### POST /keystroke/enroll
Enroll user's keystroke pattern.

**Request:**
```json
{
  "user_id": 1,
  "samples": [
    {
      "text": "hello world",
      "events": [
        {"key": "h", "action": "press", "timestamp": 1000},
        {"key": "h", "action": "release", "timestamp": 1150},
        {"key": "e", "action": "press", "timestamp": 1200}
      ]
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Keystroke template created successfully",
  "template_id": 1,
  "enrollment_count": 5,
  "quality_score": 85.5,
  "recommendations": []
}
```

#### POST /keystroke/verify
Verify keystroke pattern.

**Request:**
```json
{
  "user_id": 1,
  "keystroke_data": {
    "text": "hello world",
    "events": [
      {"key": "h", "action": "press", "timestamp": 1000},
      {"key": "h", "action": "release", "timestamp": 1150}
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "authenticated": true,
  "confidence_score": 87.5,
  "match_score": 87.5,
  "threshold": 75.0,
  "action": "allow",
  "challenge_required": false,
  "risk_factors": []
}
```

### Users

#### GET /users
List users with pagination.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page
- `search` (string): Search query
- `role` (string): Filter by role

**Response:**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

#### GET /users/{id}
Get user by ID.

#### POST /users
Create new user (admin only).

#### PUT /users/{id}
Update user.

#### DELETE /users/{id}
Delete (deactivate) user.

### Tenants

#### GET /tenants
List all tenants (super admin only).

#### POST /tenants
Create new tenant (super admin only).

#### GET /tenants/{id}
Get tenant details.

#### GET /tenants/{id}/usage
Get tenant usage statistics.

**Response:**
```json
{
  "tenant_id": "abc123",
  "api_calls_this_month": 5000,
  "api_calls_limit": 10000,
  "api_calls_percentage": 50.0,
  "users_count": 50,
  "users_limit": 100,
  "users_percentage": 50.0,
  "auth_success_rate": 95.5,
  "avg_auth_score": 82.3
}
```

### Analytics

#### GET /analytics/dashboard
Get dashboard analytics.

**Query Parameters:**
- `days` (int): Number of days (default: 30)
- `tenant_id` (string): Filter by tenant

#### GET /analytics/auth-trends
Get authentication trends.

#### GET /analytics/fraud-attempts
Get fraud attempt analytics.

### Billing

#### GET /billing/plans
Get available subscription plans.

#### POST /billing/subscribe
Subscribe to a plan.

#### GET /billing/invoices
Get invoices.

#### GET /billing/usage
Get current usage.

## Error Responses

```json
{
  "detail": "Error message"
}
```

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error
