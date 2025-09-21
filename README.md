# Artisan AI Assistant (Flask + Google Gemini)

An AI-powered assistant to help Indian artisans create authentic stories, product descriptions, social captions, hashtags, and ad copy. Includes optional image analysis and Cloud Run deployment.

## Features
- Content generation: story, description, captions, hashtags, ad copy
- Multi-language and tone presets
- Platform presets: Generic, Instagram, Etsy, Amazon
- Image analysis: extract attributes and propose captions
- Clean UI with copy-to-clipboard
- Local dev ready and Cloud Run deploy

## Setup (Local)
1. Python 3.10+
2. Create and activate a virtual environment
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```
3. Install dependencies
```powershell
pip install -r requirements.txt
```
4. Configure environment
   - Copy `.env.example` to `.env` and add your key
```env
GOOGLE_API_KEY=AIzaSyDDm-67XDbsypufy4F5eWqvzPTSE77-jKI
GEMINI_MODEL=gemini-1.5-flash
```
5. Run
```powershell
python app.py
# visit http://localhost:5000
```

## Cloud Run Deployment
1. Build and push image
```powershell
gcloud builds submit --tag gcr.io/PROJECT_ID/artisan-ai
```
2. Deploy
```powershell
gcloud run deploy artisan-ai \
  --image gcr.io/PROJECT_ID/artisan-ai \
  --allow-unauthenticated \
  --region asia-south1
```
3. Set env var (if not set during deploy)
```powershell
gcloud run services update artisan-ai \
  --set-env-vars GOOGLE_API_KEY=AIzaSyDDm-67XDbsypufy4F5eWqvzPTSE77-jKI \
  --region asia-south1
```

## Notes
- API key comes from Google AI Studio (Gemini). Keep it secret.
- Image limit ~8 MB; supported types: PNG/JPEG/WEBP.
- For hackathon, consider adding template presets and saving results to a DB.
