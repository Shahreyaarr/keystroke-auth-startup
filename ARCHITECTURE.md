# System Architecture

## Overview

The Keystroke Dynamics Authentication Platform is built using a modern microservices architecture with clear separation of concerns.

## Components

### 1. API Layer (FastAPI)

- **Authentication Module**: JWT-based auth with refresh tokens
- **Keystroke Module**: Biometric enrollment and verification
- **User Module**: CRUD operations with RBAC
- **Tenant Module**: Multi-tenancy management
- **Analytics Module**: Reporting and dashboards
- **Billing Module**: Subscription and invoicing

### 2. ML Engine

- **Feature Extraction**: Dwell time, flight time, digraphs, trigraphs
- **Template Creation**: Statistical aggregation from multiple samples
- **Verification**: Similarity scoring with weighted features
- **Quality Assessment**: Template reliability scoring

### 3. Data Layer

- **PostgreSQL**: Primary database for all entities
- **Redis**: Session cache and rate limiting
- **File Storage**: Document uploads and exports

### 4. Security

- **Encryption**: AES-256 at rest, TLS 1.3 in transit
- **Hashing**: bcrypt for passwords
- **JWT**: Stateless authentication
- **Rate Limiting**: Prevent brute force attacks

## Data Flow

```
User Input → API Gateway → FastAPI → ML Engine → Database
                ↓              ↓           ↓
           Rate Limit    Validation    Template
           Auth Check    Processing    Matching
```

## Scalability

- Horizontal scaling via Docker containers
- Database read replicas for analytics
- Redis clustering for session storage
- CDN for static assets
