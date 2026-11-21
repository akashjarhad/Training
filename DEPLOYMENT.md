# AapleSeva Deployment Guide

This document covers deploying AapleSeva to production environments.

## Deployment Options

### Option 1: Render (Recommended for Full Stack)
Deploy both API and UI with Docker containers.

### Option 2: Hugging Face Spaces (Recommended for UI Only)
Deploy Streamlit UI; API must be hosted separately (e.g., Render, Railway, Fly.io).

### Option 3: Self-Hosted Docker
Use `docker-compose.yml` on any server with Docker installed.

---

## Option 1: Deploy to Render

**Render** provides free tier hosting for web services with automatic deployments from GitHub.

### Prerequisites
- GitHub repository with Training/ code
- Render account: https://render.com
- API keys: Groq or Gemini (optional, can use LLM_MOCK=1)

### Steps

1. **Connect GitHub Repository**
   - Go to Render Dashboard
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository: `Training`

2. **Configure via render.yaml**
   - Render will auto-detect `Training/render.yaml`
   - This creates two services:
     - `aapleseva-api`: FastAPI backend
     - `aapleseva-ui`: Streamlit frontend

3. **Set Environment Variables**
   - In Render dashboard, go to each service
   - Add secrets:
     ```
     GROQ_API_KEY=your_groq_key_here
     GEMINI_API_KEY=your_gemini_key_here
     ```
   - Or set `LLM_MOCK=1` for demo mode

4. **Deploy**
   - Render auto-deploys on every push to `main`
   - Manual deploy: Click "Deploy latest commit"
   - Wait 5-10 minutes for build

5. **Get URLs**
   - API: `https://aapleseva-api.onrender.com`
   - UI: `https://aapleseva-ui.onrender.com`
   - Test: `https://aapleseva-api.onrender.com/health`

### Render Configuration

**render.yaml** (already created):
```yaml
services:
  - type: web
    name: aapleseva-api
    runtime: docker
    dockerfilePath: ./Training/Dockerfile
    healthCheckPath: /health
    envVars:
      - key: LLM_PROVIDER
        value: groq
      - key: GROQ_API_KEY
        sync: false  # Secret, set in dashboard

  - type: web
    name: aapleseva-ui
    runtime: docker
    dockerfilePath: ./Training/Dockerfile.ui
    envVars:
      - key: API_BASE_URL
        fromService:
          name: aapleseva-api
          property: host
```

### Limitations
- **Free tier**: Services sleep after 15 min inactivity
- **Cold start**: First request takes 30-60 seconds
- **Build time**: 3-5 minutes on deploy

---

## Option 2: Deploy to Hugging Face Spaces

**Hugging Face Spaces** provides free hosting for ML apps (Streamlit, Gradio).

### Prerequisites
- Hugging Face account: https://huggingface.co
- API backend deployed separately (e.g., Render)

### Steps

1. **Create New Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: `aapleseva-assistant`
   - License: MIT
   - SDK: Streamlit
   - Make it public or private

2. **Push Code**
   ```bash
   # Clone the Space repo
   git clone https://huggingface.co/spaces/YOUR_USERNAME/aapleseva-assistant
   cd aapleseva-assistant
   
   # Copy files
   cp -r ../Training/ui .
   cp -r ../Training/data .
   cp ../Training/app.yaml .
   cp ../Training/.streamlit/config.toml .streamlit/
   
   # Commit and push
   git add .
   git commit -m "Deploy AapleSeva UI"
   git push
   ```

3. **Configure Environment**
   - In Space settings → "Repository secrets"
   - Add:
     ```
     API_BASE_URL=https://your-api.onrender.com
     GROQ_API_KEY=your_key
     ```

4. **Access**
   - URL: `https://huggingface.co/spaces/YOUR_USERNAME/aapleseva-assistant`
   - Share publicly or embed in websites

### app.yaml Configuration

Already created at `Training/app.yaml`:
```yaml
title: AapleSeva - Maharashtra Right to Service Assistant
emoji: 🏛️
sdk: streamlit
sdk_version: "1.28.0"
app_file: ui/app.py
```

### Limitations
- **UI only**: Backend must be hosted elsewhere
- **Restarts**: Space restarts after inactivity
- **Resources**: Limited CPU/memory on free tier

---

## Option 3: Self-Hosted Docker

Deploy on any server with Docker (DigitalOcean, AWS, GCP, Azure).

### Prerequisites
- Server with Docker and Docker Compose installed
- Domain name (optional, can use IP)
- SSL certificate (optional, use Caddy or nginx)

### Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Training.git
   cd Training/Training
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env
   # Set your API keys or LLM_MOCK=1
   ```

3. **Start Services**
   ```bash
   docker compose up -d
   ```

4. **Access**
   - API: `http://your-server-ip:8000`
   - UI: `http://your-server-ip:8501`

5. **Set Up Reverse Proxy** (Optional)
   Use nginx or Caddy to add SSL and custom domain:
   ```nginx
   # nginx config
   server {
       server_name api.yourdomain.com;
       location / {
           proxy_pass http://localhost:8000;
       }
   }
   
   server {
       server_name app.yourdomain.com;
       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

### Production Hardening
- Use Docker secrets for API keys
- Set up log rotation
- Configure backups for Chroma volume
- Monitor with Prometheus/Grafana
- Use container restart policies
- Set resource limits in docker-compose.yml

---

## CI/CD with GitHub Actions

### Automatic Deployments

**On every push to main:**
1. Linting (ruff)
2. Tests (pytest)
3. Docker build
4. Deploy to Render (if configured)

### Workflow Files

`.github/workflows/ci.yml`:
- Runs on push and pull requests
- Checks: lint, test, docker build
- Green badge in README

`.github/workflows/deploy-render.yml`:
- Runs on push to main
- Triggers Render deployment via webhook

### Setting Up Deploy Hook

1. In Render dashboard → Service → Settings
2. Copy "Deploy Hook" URL
3. In GitHub → Settings → Secrets → Actions
4. Add secret: `RENDER_DEPLOY_HOOK` = `<webhook-url>`

---

## Health Checks

All deployment options should pass:

```bash
# API health
curl https://your-api-url.com/health
# Expected: {"status":"ok","service":"AapleSeva","records":1090}

# UI health (if accessible)
curl https://your-ui-url.com/_stcore/health
```

---

## Monitoring

### Render
- Built-in logs and metrics
- Set up email/Slack alerts
- View deploy history

### Hugging Face Spaces
- Activity logs in Space settings
- Community analytics (if public)

### Self-Hosted
- Docker logs: `docker compose logs -f`
- Application logs: Check `/app/logs` in containers
- Set up monitoring (Prometheus, Grafana, Sentry)

---

## Troubleshooting

### API Returns 502
- Check logs: `docker compose logs api`
- Verify environment variables
- Ensure Chroma volume mounted
- Check LLM provider keys

### UI Can't Connect to API
- Verify `API_BASE_URL` environment variable
- Check API health endpoint
- Ensure CORS configured if cross-origin

### Cold Start Slow (Render Free Tier)
- First request takes 30-60s (service wakes up)
- Consider paid tier or keep-alive ping service
- Use `LLM_MOCK=1` to avoid LLM API delays

### Docker Build Fails
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Ensure data/ files copied correctly
- Check Docker build logs

---

## Cost Estimates

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| **Render** | ✅ Yes (sleeps after 15 min) | $7/month per service |
| **Hugging Face Spaces** | ✅ Yes (limited resources) | $5/month (more resources) |
| **Railway** | ✅ $5 credit/month | $0.01/min active |
| **Fly.io** | ✅ 3 VMs free | $0.02/hour |
| **DigitalOcean** | ❌ No free tier | $4/month droplet |

**Recommended for production:** Render paid tier ($14/month for API + UI) or self-hosted.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | No | `groq` | `groq` or `gemini` |
| `LLM_MOCK` | No | `0` | Set to `1` for testing without API keys |
| `GROQ_API_KEY` | Conditional | - | Required if `LLM_PROVIDER=groq` |
| `GEMINI_API_KEY` | Conditional | - | Required if `LLM_PROVIDER=gemini` |
| `API_BASE_URL` | UI only | `http://localhost:8000` | API endpoint for UI |
| `PORT` | No | `8000` (API), `8501` (UI) | Service port |

---

## Updating Deployment

### Render
- Push to `main` branch → auto-deploys
- Manual: Dashboard → "Deploy latest commit"

### Hugging Face Spaces
- Push to Space repo → auto-rebuilds
- Or use "Factory Reboot" in settings

### Self-Hosted
```bash
git pull origin main
docker compose down
docker compose up --build -d
```

---

## Security Best Practices

1. **Never commit secrets** - Use .env and environment variables
2. **Use HTTPS** - Set up SSL certificates (Let's Encrypt)
3. **Rate limiting** - Add API rate limits in production
4. **Input validation** - Already implemented in FastAPI/Pydantic
5. **CORS configuration** - Restrict allowed origins
6. **Container security** - Run as non-root user, scan images
7. **Keep dependencies updated** - Regular security patches

---

## Support

- **Issues**: GitHub Issues on repository
- **Render Docs**: https://render.com/docs
- **HF Spaces Docs**: https://huggingface.co/docs/hub/spaces
- **Docker Docs**: https://docs.docker.com

---

## Live URLs

After deployment, update README.md with:

```markdown
## 🚀 Live Demo

- **UI**: https://aapleseva-ui.onrender.com
- **API**: https://aapleseva-api.onrender.com
- **Docs**: https://aapleseva-api.onrender.com/docs
- **Health**: https://aapleseva-api.onrender.com/health
```
