#!/bin/bash

# Keystroke Dynamics Authentication Platform - Setup Script
# One-command setup for local development

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Keystroke Dynamics Authentication Platform Setup          ║"
echo "║              Enterprise-Grade Behavioral Biometrics           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
check_docker() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker first:${NC}"
        echo "  - Ubuntu/Debian: sudo apt-get install docker.io"
        echo "  - macOS: https://docs.docker.com/desktop/mac/install/"
        echo "  - Windows: https://docs.docker.com/desktop/windows/install/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
}

# Create environment files
create_env_files() {
    echo -e "${BLUE}Creating environment files...${NC}"
    
    # Backend .env
    if [ ! -f backend/.env ]; then
        cat > backend/.env << EOF
# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/keystroke_auth

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-in-production-$(openssl rand -hex 16)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
DEBUG=false
ENVIRONMENT=production
APP_NAME=Keystroke Dynamics Auth Platform

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# ML Model
MODEL_PATH=app/ml/models
MIN_KEYSTROKES_FOR_ENROLLMENT=50
AUTHENTICATION_THRESHOLD=0.75

# Email (optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
FROM_EMAIL=noreply@keystrokeauth.com

# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760

# Logging
LOG_LEVEL=INFO

# Billing
TRIAL_DAYS=14
EOF
        echo -e "${GREEN}✓ Created backend/.env${NC}"
    fi
}

# Start services
start_services() {
    echo -e "${BLUE}Starting services...${NC}"
    
    # Build and start containers
    docker-compose down 2>/dev/null || true
    docker-compose up --build -d
    
    echo ""
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    
    # Wait for database
    echo -n "  Waiting for database"
    for i in {1..30}; do
        if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    # Wait for backend
    echo -n "  Waiting for backend API"
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    echo ""
}

# Seed initial data
seed_data() {
    echo -e "${BLUE}Seeding initial data...${NC}"
    
    # Create super admin
    docker-compose exec -T backend python -c "
import sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.tenant import Tenant, TenantConfig, SubscriptionPlan

# Create tables
engine = create_engine('postgresql://postgres:postgres@db:5432/keystroke_auth')
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
db = Session()

# Check if super admin exists
if not db.query(User).filter(User.email == 'admin@keystrokeauth.com').first():
    # Create default tenant
    tenant = Tenant(
        id='default',
        name='Default Organization',
        slug='default',
        email='admin@keystrokeauth.com',
        plan=SubscriptionPlan.BUSINESS,
        is_active=True
    )
    db.add(tenant)
    db.flush()
    
    # Create tenant config
    config = TenantConfig(tenant_id=tenant.id)
    db.add(config)
    
    # Create super admin
    admin = User(
        email='admin@keystrokeauth.com',
        hashed_password=get_password_hash('admin123'),
        full_name='Super Admin',
        role=UserRole.SUPER_ADMIN,
        tenant_id=tenant.id,
        is_active=True,
        is_verified=True
    )
    db.add(admin)
    
    # Create demo user
    demo_user = User(
        email='demo@keystrokeauth.com',
        hashed_password=get_password_hash('demo123'),
        full_name='Demo User',
        role=UserRole.END_USER,
        tenant_id=tenant.id,
        is_active=True,
        is_verified=True
    )
    db.add(demo_user)
    
    db.commit()
    print('✓ Super admin created: admin@keystrokeauth.com / admin123')
    print('✓ Demo user created: demo@keystrokeauth.com / demo123')
else:
    print('✓ Users already exist')

db.close()
" 2>/dev/null || echo "  (Database already initialized)"
    
    echo ""
}

# Display success message
show_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║              🎉 Setup Complete! 🎉                             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}Your Keystroke Dynamics Authentication Platform is ready!${NC}"
    echo ""
    echo "📱 Access URLs:"
    echo "  • Landing Page:    http://localhost:8080"
    echo "  • Admin Dashboard: http://localhost:3000"
    echo "  • API Docs:        http://localhost:8000/docs"
    echo "  • API Base:        http://localhost:8000/api/v1"
    echo ""
    echo "🔑 Default Credentials:"
    echo "  • Super Admin: admin@keystrokeauth.com / admin123"
    echo "  • Demo User:   demo@keystrokeauth.com / demo123"
    echo ""
    echo "📚 Documentation:"
    echo "  • API Reference:   http://localhost:8000/docs"
    echo "  • ReDoc:           http://localhost:8000/redoc"
    echo ""
    echo "🛠️  Useful Commands:"
    echo "  • View logs:       docker-compose logs -f"
    echo "  • Stop services:   docker-compose down"
    echo "  • Restart:         docker-compose restart"
    echo ""
    echo -e "${YELLOW}⚠️  Important:${NC}"
    echo "  Change default passwords before production use!"
    echo "  Update SECRET_KEY in backend/.env for production."
    echo ""
    echo -e "${GREEN}Happy authenticating! 🔐${NC}"
    echo ""
}

# Main execution
main() {
    check_docker
    create_env_files
    start_services
    seed_data
    show_success
}

main "$@"
