# Deployment Guide - Tafi BNPL Pricing Tool

## ⚠️ Important: Why Not Netlify?

**Netlify won't work** for this application because:
- Netlify is designed for **static sites** (HTML, CSS, JavaScript)
- This is a **Streamlit app** that requires:
  - Python runtime environment
  - Server that stays running
  - WebSocket support for interactivity
  - Real-time computation

## ✅ Recommended Deployment Platforms

---

## Option 1: Streamlit Community Cloud (RECOMMENDED - FREE) ⭐

**Best choice for Streamlit apps - completely free and optimized for Streamlit!**

### Prerequisites
- GitHub account
- Your code pushed to a GitHub repository

### Steps

1. **Push your code to GitHub**
```bash
cd /Users/ernestoabadi/Developer/tafi_pricing_tool

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Tafi BNPL Pricing Tool v1.5"

# Add your GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/tafi-pricing-tool.git

# Push
git push -u origin main
```

2. **Deploy on Streamlit Community Cloud**
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Select your repository: `YOUR_USERNAME/tafi-pricing-tool`
   - Main file path: `app.py`
   - Click "Deploy"

3. **Done!** Your app will be live at:
   ```
   https://YOUR_USERNAME-tafi-pricing-tool.streamlit.app
   ```

### Files Already Configured ✅
- `.streamlit/config.toml` - Streamlit configuration
- `requirements.txt` - Python dependencies
- `packages.txt` - System dependencies (if needed)

---

## Option 2: Render (FREE TIER AVAILABLE) 🚀

**Modern alternative to Heroku with free tier**

### Steps

1. **Create account** at https://render.com

2. **Create new Web Service**
   - Connect your GitHub repository
   - Or use "Deploy from Git URL"

3. **Configure**:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
   - **Instance Type**: Free (or paid for better performance)

4. **Deploy** - Render will automatically deploy

### Files Already Configured ✅
- `requirements.txt`
- `runtime.txt` - Python version

---

## Option 3: Heroku (PAID - No Free Tier)

**Note**: Heroku eliminated their free tier in November 2022

### Steps

1. **Install Heroku CLI**
```bash
brew install heroku/brew/heroku
```

2. **Login**
```bash
heroku login
```

3. **Create app**
```bash
cd /Users/ernestoabadi/Developer/tafi_pricing_tool
heroku create tafi-pricing-tool
```

4. **Deploy**
```bash
git push heroku main
```

5. **Open app**
```bash
heroku open
```

### Files Already Configured ✅
- `Procfile` - Tells Heroku how to run the app
- `requirements.txt`
- `runtime.txt`

---

## Option 4: Railway (FREE TIER - $5 CREDIT) 🛤️

**Simple deployment with generous free tier**

### Steps

1. **Create account** at https://railway.app

2. **New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure**:
   Railway auto-detects Python apps and uses:
   - `requirements.txt` automatically
   - Start command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

4. **Deploy** - Automatic!

---

## Option 5: Hugging Face Spaces (FREE) 🤗

**Free hosting for ML/data apps**

### Steps

1. **Create account** at https://huggingface.co

2. **Create new Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Choose **Streamlit** as SDK
   - Name your space

3. **Upload files**:
   - `app.py`
   - `pricing_engine.py`
   - `requirements.txt`
   - All other `.py` files

4. **Space automatically deploys!**

---

## Option 6: Google Cloud Run (PAY-AS-YOU-GO) ☁️

**Serverless, auto-scaling deployment**

### Steps

1. **Create `Dockerfile`** (I'll create this for you below)

2. **Build and deploy**
```bash
gcloud run deploy tafi-pricing-tool \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Comparison Table

| Platform | Cost | Ease | Performance | Custom Domain |
|----------|------|------|-------------|---------------|
| **Streamlit Cloud** ⭐ | FREE | ⭐⭐⭐⭐⭐ | Good | Yes (paid) |
| **Render** | FREE tier | ⭐⭐⭐⭐ | Good | Yes |
| **Heroku** | $7+/mo | ⭐⭐⭐⭐ | Excellent | Yes |
| **Railway** | $5 credit | ⭐⭐⭐⭐⭐ | Good | Yes |
| **Hugging Face** | FREE | ⭐⭐⭐ | Good | Limited |
| **Google Cloud Run** | Pay-as-you-go | ⭐⭐ | Excellent | Yes |

---

## 🎯 My Recommendation

**Use Streamlit Community Cloud** because:
1. ✅ **Completely FREE**
2. ✅ **Optimized for Streamlit** (no configuration needed)
3. ✅ **Auto-redeploys** when you push to GitHub
4. ✅ **Built-in analytics**
5. ✅ **No credit card required**
6. ✅ **Best documentation**

---

## Environment Variables (If Needed)

If you need to add API keys or secrets:

### Streamlit Cloud
- Go to app settings
- Click "Secrets"
- Add in TOML format:
```toml
API_KEY = "your-secret-key"
```

### Heroku
```bash
heroku config:set API_KEY=your-secret-key
```

### Render
- Go to Environment variables in dashboard
- Add key-value pairs

---

## Custom Domain Setup

### Streamlit Cloud (Paid Feature)
- Upgrade to Teams plan
- Add custom domain in settings

### Render (Free)
- Go to Settings → Custom Domain
- Add your domain
- Update DNS records as shown

### Heroku
```bash
heroku domains:add www.yourdomain.com
```

---

## Monitoring & Logs

### Streamlit Cloud
- View logs in app settings
- See usage analytics

### Heroku
```bash
heroku logs --tail
```

### Render
- View logs in dashboard

---

## Performance Optimization

For better performance on any platform:

1. **Add caching** to expensive calculations (already optimized in code)

2. **Upgrade to paid tier** for:
   - More memory
   - Faster CPU
   - No cold starts

3. **Use CDN** for static assets (if you add images/files)

---

## Troubleshooting

### App won't start
- Check `requirements.txt` has all dependencies
- Verify Python version in `runtime.txt`
- Check logs for errors

### Slow performance
- Upgrade to paid tier
- Optimize calculations
- Add more caching

### Memory issues
- Reduce chart complexity
- Upgrade instance size
- Clear caches regularly

---

## Files Included for Deployment ✅

- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version (3.10.12)
- `Procfile` - Heroku configuration
- `.streamlit/config.toml` - Streamlit settings
- `packages.txt` - System dependencies
- `app.py` - Main application
- `pricing_engine.py` - Core logic

---

## Quick Start Command

For **Streamlit Community Cloud** (easiest):

```bash
# 1. Push to GitHub
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. Go to https://share.streamlit.io and click "New app"
# 3. Select your repo and click "Deploy"
# Done! ✨
```

---

**Need help?** Check platform-specific docs:
- Streamlit: https://docs.streamlit.io/streamlit-community-cloud
- Render: https://render.com/docs
- Railway: https://docs.railway.app

**Current Version**: 1.5
**Last Updated**: 2025-10-18
