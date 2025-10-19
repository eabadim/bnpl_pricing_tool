#!/bin/bash

# Deployment helper script for Tafi BNPL Pricing Tool

echo "==================================================================="
echo "  Tafi BNPL Pricing Tool - Deployment Helper"
echo "==================================================================="
echo ""
echo "This app CANNOT be deployed on Netlify (static site host)."
echo "Please choose one of the following platforms for Streamlit apps:"
echo ""
echo "1. Streamlit Community Cloud (RECOMMENDED - FREE)"
echo "2. Render (FREE tier available)"
echo "3. Railway ($5 free credit)"
echo "4. Heroku (paid only)"
echo "5. Google Cloud Run (pay-as-you-go)"
echo "6. Hugging Face Spaces (FREE)"
echo ""
read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo ""
        echo "==================================================================="
        echo "  Streamlit Community Cloud Deployment"
        echo "==================================================================="
        echo ""
        echo "Steps:"
        echo "1. Make sure your code is pushed to GitHub"
        echo "2. Go to: https://share.streamlit.io"
        echo "3. Click 'New app'"
        echo "4. Select your repository and click 'Deploy'"
        echo ""
        read -p "Have you pushed to GitHub? (y/n): " pushed
        if [ "$pushed" = "y" ]; then
            echo ""
            echo "Opening Streamlit Cloud..."
            open "https://share.streamlit.io"
        else
            echo ""
            echo "First, push to GitHub:"
            echo "  git add ."
            echo "  git commit -m 'Ready for deployment'"
            echo "  git push origin main"
        fi
        ;;
    2)
        echo ""
        echo "==================================================================="
        echo "  Render Deployment"
        echo "==================================================================="
        echo ""
        echo "Steps:"
        echo "1. Go to: https://render.com"
        echo "2. Create a new Web Service"
        echo "3. Connect your GitHub repository"
        echo "4. Build Command: pip install -r requirements.txt"
        echo "5. Start Command: streamlit run app.py --server.port=\$PORT --server.address=0.0.0.0"
        echo ""
        echo "Opening Render..."
        open "https://render.com"
        ;;
    3)
        echo ""
        echo "==================================================================="
        echo "  Railway Deployment"
        echo "==================================================================="
        echo ""
        echo "Steps:"
        echo "1. Go to: https://railway.app"
        echo "2. Click 'New Project'"
        echo "3. Select 'Deploy from GitHub repo'"
        echo "4. Railway will auto-detect and deploy!"
        echo ""
        echo "Opening Railway..."
        open "https://railway.app"
        ;;
    4)
        echo ""
        echo "==================================================================="
        echo "  Heroku Deployment"
        echo "==================================================================="
        echo ""
        echo "Note: Heroku has no free tier (minimum $7/month)"
        echo ""
        read -p "Continue with Heroku? (y/n): " continue
        if [ "$continue" = "y" ]; then
            if ! command -v heroku &> /dev/null; then
                echo "Installing Heroku CLI..."
                brew install heroku/brew/heroku
            fi

            echo "Logging in to Heroku..."
            heroku login

            echo "Creating Heroku app..."
            heroku create tafi-pricing-tool

            echo "Deploying to Heroku..."
            git push heroku main

            echo "Opening app..."
            heroku open
        fi
        ;;
    5)
        echo ""
        echo "==================================================================="
        echo "  Google Cloud Run Deployment"
        echo "==================================================================="
        echo ""
        echo "Steps:"
        echo "1. Make sure you have Google Cloud SDK installed"
        echo "2. Run: gcloud run deploy tafi-pricing-tool --source . --platform managed --region us-central1 --allow-unauthenticated"
        echo ""
        read -p "Deploy now? (y/n): " deploy
        if [ "$deploy" = "y" ]; then
            gcloud run deploy tafi-pricing-tool \
                --source . \
                --platform managed \
                --region us-central1 \
                --allow-unauthenticated
        fi
        ;;
    6)
        echo ""
        echo "==================================================================="
        echo "  Hugging Face Spaces Deployment"
        echo "==================================================================="
        echo ""
        echo "Steps:"
        echo "1. Go to: https://huggingface.co/spaces"
        echo "2. Click 'Create new Space'"
        echo "3. Choose 'Streamlit' as SDK"
        echo "4. Upload your files"
        echo ""
        echo "Opening Hugging Face..."
        open "https://huggingface.co/spaces"
        ;;
    *)
        echo ""
        echo "Invalid choice. Please run the script again and choose 1-6."
        ;;
esac

echo ""
echo "==================================================================="
echo "  Deployment files are ready in your project:"
echo "==================================================================="
echo ""
echo "  ✅ requirements.txt - Python dependencies"
echo "  ✅ runtime.txt - Python version"
echo "  ✅ Procfile - Heroku configuration"
echo "  ✅ Dockerfile - Container deployment"
echo "  ✅ .streamlit/config.toml - Streamlit config"
echo ""
echo "For detailed instructions, see: DEPLOYMENT.md"
echo ""
