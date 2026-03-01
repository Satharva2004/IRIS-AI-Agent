<div align="center">
  <h1>IRIS AI</h1>
  <p>A high-performance, fully customizable AI assistant interface built on Streamlit.</p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
</div>

---

IRIS AI is an open-source AI assistant. I built this project to push the boundaries of what a Streamlit interface can look and feel like. It completely overrides the default Streamlit styling with a custom-built, modern UI, while packing serious functionality under the hood.

If you find the code useful or want to adapt the custom CSS framework for your own Streamlit projects, dropping a **Star** and a **Fork** is highly appreciated.

## Features

- **Blazing Fast Output**: Runs on the Groq API (using Llama 3) for near-instant inference.
- **Voice I/O**: Native browser microphone input and seamless gTTS audio output.
- **Custom UI System**: 5 built-in premium CSS themes (Black, Pink, Blue, Green, White) featuring customized chat bubbles, glassmorphism sidebars, and fluid animations.
- **Dynamic Integrations**: 
  - Live weather tracking via Open-Meteo (No API key needed).
  - Image and Web Search via Google Custom Search API integration.
  - Interactive YouTube search with embedded thumbnail cards.
- **State Management**: Local JSON-based memory for user profiles and chat session history.

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/Satharva2004/IRIS-AI-Chatbot.git
cd IRIS-AI-Chatbot
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set up Environment Variables**  
Create a `.env` file in the root directory.
```env
# Core LLM 
GEMINI_API_KEY=your_groq_api_key

# Integrations
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_google_cse_id
YOUTUBE_API_KEY=your_youtube_api_key
```

3. **Run the App**
```bash
streamlit run app.py
```

## Deployment

Deploying to **Streamlit Community Cloud** takes minutes:
1. Push your clone to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and deploy a new app pointing to `app.py`.
3. Add your `.env` variables in the Streamlit Dashboard under **Settings > Secrets**.

## Contributing

Contributions are welcome. If you want to add new tool integrations, optimize the code, or design a new CSS theme, feel free to open a PR.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewFeature`)
3. Commit your Changes (`git commit -m 'Add NewFeature'`)
4. Push to the Branch (`git push origin feature/NewFeature`)
5. Open a Pull Request
