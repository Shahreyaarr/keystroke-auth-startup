# Deployment Guide

## Local Development

```bash
# Clone repository
git clone <repo-url>
cd keystroke-auth-platform

# Run setup
./setup.sh
```

## Production Deployment

### Docker Compose

```bash
# Build and start
docker-compose -f docker-compose.yml up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Environment Variables

Create `.env` file:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-secret-key
DEBUG=false
```

### Cloud Platforms

#### Render
1. Create Web Service
2. Connect GitHub repo
3. Set environment variables
4. Deploy

#### Railway
1. Click "Deploy on Railway"
2. Configure variables
3. Deploy

#### AWS ECS
1. Build Docker image
2. Push to ECR
3. Create ECS cluster
4. Deploy service

## SSL/TLS

Use Let's Encrypt for free SSL:

```bash
certbot --nginx -d yourdomain.com
```

## Monitoring

- Health check: `/health`
- Metrics: Prometheus + Grafana
- Logs: ELK Stack
