# IRIS AI

This repository contains the IRIS AI application built with Streamlit.

## Deploying to Streamlit Community Cloud

Hosting this project on Streamlit Community Cloud is straightforward:

1. **Push to GitHub**: Make sure this codebase is pushed to a public or private GitHub repository.
2. **Sign in to Streamlit**: Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.
3. **Deploy the App**:
   - Click **"New app"**.
   - Select your GitHub repository, branch, and specify `app.py` as the Main file path.
   - Click **"Deploy!"**
4. **Configure Secrets**:
   Since the app relies on several external APIs, you'll need to configure your secrets in the Streamlit Cloud dashboard.
   - Navigate to your deployed app dashboard.
   - Click the three dots (⚙️) menu -> **Settings** -> **Secrets**.
   - Paste the following, substituting your actual keys (same as your local `.env` file):

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GOOGLE_API_KEY = "your_google_api_key"
GOOGLE_CSE_ID = "your_google_cse_id"
YOUTUBE_API_KEY = "your_youtube_api_key"
```

5. **Wait for Build**: Streamlit will automatically install dependencies from `requirements.txt` (which now correctly includes `gTTS` and other required libraries) and launch the app.

> **Note**: Free-tier Streamlit Cloud apps have ephemeral storage. Your `users.json` and `memory.json` data will reset anytime the container restarts or goes to sleep due to inactivity.

## Running Locally

1. Create a virtual environment and activate it.
2. Install the necessary libraries using `pip install -r requirements.txt`.
3. Set your environment variables via a `.env` file containing the api keys listed above.
4. Run the application: `streamlit run app.py`
