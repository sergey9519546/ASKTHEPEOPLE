# Deployment Checklist

## Pre-Deployment Requirements

### 1. Environment Variables (REQUIRED)

**Critical Security Variables:**
```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=<32+ character random string>

# Required in production
CORS_ORIGINS=https://your-domain.com

# Optional but recommended for production
APP_TOKEN=<32+ character access token>
REQUIRE_APP_AUTH=true
```

**LLM Provider (Choose ONE):**
```bash
# Option A: GitHub Models
LLM_API_KEY=<your-github-models-key>
LLM_BASE_URL=https://models.github.ai/inference
LLM_MODEL_NAME=openai/gpt-4.1-mini

# Option B: NVIDIA NIM
# LLM_API_KEY=<your-nvidia-key>
# LLM_BASE_URL=https://integrate.api.nvidia.com/v1
# LLM_MODEL_NAME=meta/llama-4-maverick-17b-128e-instruct

# Option C: OpenAI
# LLM_API_KEY=sk-...
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL_NAME=gpt-4o-mini
```

**Required Services:**
```bash
ZEP_API_KEY=<your-zep-api-key-here>
```

**Optional:**
```bash
BRAVE_SEARCH_API_KEY=<for-report-agent-search>
REDIS_URL=redis://your-redis-host:6379/0  # For Celery workers
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # For PostgreSQL
```

### 2. File System Requirements

**Railway Deployment:**
- [ ] Add persistent volume at `/app/backend/uploads`
- [ ] Volume must survive deploys (user data persistence)

**Self-Hosted:**
- [ ] Ensure `backend/uploads/simulations` is writable
- [ ] Set appropriate permissions (755 or 700)

### 3. Database Setup

**SQLite (Default - Development):**
- No setup required, uses `askthepeople.db`

**PostgreSQL (Production):**
```bash
# Install dependencies (already in requirements.txt)
# psycopg-binary included for PostgreSQL support

# Set DATABASE_URL in environment
DATABASE_URL=postgresql://user:password@host:5432/database

# Run migrations
cd backend
alembic upgrade head
```

### 4. Redis Setup (For Horizontal Scaling)

**Required if:**
- Running multiple web workers
- Using Celery task queues
- Need distributed rate limiting

```bash
# Install Redis
# Ubuntu: sudo apt-get install redis-server
# Docker: docker run -d -p 6379:6379 redis:alpine

# Set in environment
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Rate Limiting Configuration

**Single Worker (Default):**
```bash
RATELIMIT_STORAGE_URI=memory://
```

**Multiple Workers:**
```bash
RATELIMIT_STORAGE_URI=redis://localhost:6379/0
```

**Warning:** Memory-based rate limiting is process-local. With multiple workers, each maintains separate counters. Use Redis for consistent rate limiting across instances.

## Deployment Platforms

### Railway.app

**Environment Setup:**
1. Connect GitHub repository
2. Set all required environment variables in Railway dashboard
3. Add persistent volume:
   - Path: `/app/backend/uploads`
   - Size: 1GB minimum (adjust based on expected simulation data)

**Domain Configuration:**
- Railway auto-provides `*.railway.app` domain
- Update `CORS_ORIGINS` to include your custom domain if using one
- `TRUSTED_HOSTS` auto-derived from Railway domain variables

**Health Checks:**
- Railway readiness probes use `healthcheck.railway.app`
- Auto-configured in `config.py`

### Self-Hosted (Docker)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Create upload directory
RUN mkdir -p /app/backend/uploads/simulations

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "wsgi:app"]
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5001:5001"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - LLM_API_KEY=${LLM_API_KEY}
      - ZEP_API_KEY=${ZEP_API_KEY}
      - CORS_ORIGINS=https://your-domain.com
    volumes:
      - uploads:/app/backend/uploads
    depends_on:
      - redis
  
  worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data

volumes:
  uploads:
  redis_data:
```

### Self-Hosted (Direct)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export LLM_API_KEY=your-key
export ZEP_API_KEY=your-key
export CORS_ORIGINS=https://your-domain.com

# Run database migrations
alembic upgrade head

# Start application (development)
python run.py

# Start application (production)
gunicorn --bind 0.0.0.0:5001 --workers 4 wsgi:app

# Start Celery worker (optional)
celery -A app.celery_app worker --loglevel=info
```

## Post-Deployment Verification

### 1. Health Check
```bash
curl https://your-domain.com/api/health
# Expected: {"status": "ok"}
```

### 2. Authentication Test (if REQUIRE_APP_AUTH=true)
```bash
# Without token (should fail)
curl https://your-domain.com/api/simulations
# Expected: 401 Unauthorized

# With token (should succeed)
curl -H "Authorization: Bearer YOUR_APP_TOKEN" \
     https://your-domain.com/api/simulations
```

### 3. CORS Verification
```bash
curl -H "Origin: https://your-frontend.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://your-domain.com/api/health
# Check Access-Control-Allow-Origin header matches your origin
```

### 4. File Upload Test
```bash
# Upload a test file
curl -X POST -F "file=@test.pdf" \
     -H "Authorization: Bearer YOUR_APP_TOKEN" \
     https://your-domain.com/api/sources/upload

# Verify file persists after deploy restart
```

### 5. Database Persistence
```bash
# Create a test project
curl -X POST -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_APP_TOKEN" \
     -d '{"name": "Test Project"}' \
     https://your-domain.com/api/projects

# Restart application and verify project still exists
```

## Monitoring & Observability

### Logging
- Default: JSON format in production, text in development
- Log level: INFO (production), DEBUG (development)
- Logs written to stdout (capture via platform logging)

### Recommended Monitoring Tools

**Uptime Monitoring:**
- UptimeRobot (free tier available)
- Pingdom
- StatusCake

**Error Tracking:**
- Sentry (recommended)
  ```bash
  # Add to requirements.txt
  sentry-sdk[flask]
  
  # Set in environment
  SENTRY_DSN=https://your-sentry-dsn
  ```

**Performance Monitoring:**
- New Relic
- Datadog
- Prometheus + Grafana (self-hosted)

### Load Testing

Before accepting production traffic:
```bash
# Install k6 or use Apache Bench
# Test with 10 concurrent users
ab -n 1000 -c 10 https://your-domain.com/api/health

# Test upload endpoint
# (Prepare 10 test files)
for i in {1..10}; do
  curl -X POST -F "file=@test$i.pdf" \
       -H "Authorization: Bearer YOUR_APP_TOKEN" \
       https://your-domain.com/api/sources/upload &
done
wait
```

**Acceptable Performance:**
- Health check: < 100ms p95
- Project creation: < 500ms p95
- File upload (1MB): < 2s p95
- Simulation start: < 1s p95 (async)
- Report generation: < 15min (timeout configured)

## Security Hardening

### Already Implemented ✅
- Path traversal protection (`safe_path.py`)
- Input validation with size limits
- Rate limiting (configurable)
- CORS enforcement (production)
- Host header validation
- Credential validation (length, entropy)
- Zero-trust source ingestion
- No chain-of-thought retention
- Human validation boundary (truth contract)

### Additional Recommendations

**Network:**
- [ ] Enable HTTPS (Railway provides automatically)
- [ ] Use Cloudflare or similar for DDoS protection
- [ ] Configure firewall rules (allow only 80/443)

**Application:**
- [ ] Set `REQUIRE_APP_AUTH=true` in production
- [ ] Rotate `SECRET_KEY` and `APP_TOKEN` periodically
- [ ] Monitor failed auth attempts
- [ ] Review rate limit settings based on usage patterns

**Infrastructure:**
- [ ] Enable automatic security updates
- [ ] Regular dependency audits (`pip-audit`, `safety`)
- [ ] Backup database regularly
- [ ] Document incident response procedures

## Troubleshooting

### Common Issues

**SECRET_KEY Error:**
```
RuntimeError: SECRET_KEY must be set in production
```
**Solution:** Generate and set SECRET_KEY in environment variables

**CORS Error:**
```
CORS_ORIGINS='*' is not allowed in production
```
**Solution:** Set explicit origins: `CORS_ORIGINS=https://your-domain.com`

**Database Migration Error:**
```
alembic.util.exc.CommandError: Target database is not up to date
```
**Solution:** Run `alembic upgrade head`

**Upload Directory Not Writable:**
```
PermissionError: [Errno 13] Permission denied
```
**Solution:** 
```bash
chmod 755 backend/uploads
chown www-data:www-data backend/uploads  # if running as www-data
```

**Redis Connection Error:**
```
redis.exceptions.ConnectionError
```
**Solution:** 
- Verify Redis is running
- Check REDIS_URL is correct
- Ensure network connectivity between app and Redis

**Celery Worker Not Processing Tasks:**
```
# Check worker logs
celery -A app.celery_app worker --loglevel=debug

# Verify broker connection
celery -A app.celery_app inspect ping
```

## Scaling Considerations

### Current Architecture Limits

**Single Worker:**
- Concurrent requests: ~4-8 (depends on request complexity)
- Task queue: In-memory (lost on restart)
- Rate limiting: Process-local

**Multiple Workers:**
- Requires Redis for task queue
- Requires Redis for rate limiting
- Stateless web tier (horizontal scaling possible)

### When to Scale

**Add Web Workers:**
- CPU usage consistently > 70%
- Request latency increasing under load
- More than 100 concurrent users

**Add Celery Workers:**
- Background tasks queuing up
- Report generation blocking web requests
- Simulation runs taking too long

**Upgrade Database:**
- SQLite file size > 1GB
- Write contention issues
- Need for advanced queries

### Scaling Strategy

1. **First:** Optimize current instance (caching, query optimization)
2. **Second:** Add Redis for task queue + rate limiting
3. **Third:** Horizontal web tier (2-4 workers)
4. **Fourth:** Migrate to PostgreSQL
5. **Fifth:** Add dedicated Celery workers

## Maintenance

### Regular Tasks

**Weekly:**
- Review error logs
- Check disk space usage
- Monitor rate limit hits

**Monthly:**
- Update dependencies
- Review security advisories
- Backup database
- Test disaster recovery

**Quarterly:**
- Load testing
- Security audit
- Review rate limit thresholds
- Update documentation

### Dependency Updates

```bash
# Check for outdated packages
pip list --outdated

# Update safely (test in staging first)
pip install --upgrade package-name

# Audit for vulnerabilities
pip-audit
# or
safety check
```

### Database Maintenance

**SQLite:**
```bash
# Vacuum database
sqlite3 askthepeople.db "VACUUM;"

# Check integrity
sqlite3 askthepeople.db "PRAGMA integrity_check;"
```

**PostgreSQL:**
```bash
# Vacuum analyze
psql -c "VACUUM ANALYZE;"

# Check for bloat
psql -c "SELECT * FROM pg_stat_user_tables;"
```

## Support & Resources

**Documentation:**
- Architecture Decision Records: `docs/architecture/adr/`
- Security Model: `docs/security/THREAT_MODEL.md`
- API Documentation: Available at `/api/docs` (if enabled)

**Community:**
- GitHub Issues: Report bugs and feature requests
- Discussions: Ask questions and share experiences

**Emergency Contacts:**
- On-call rotation: [Your team's contact info]
- Escalation path: [Your escalation procedure]

---

*Last updated: 2025*
*Version: 1.0.0*
