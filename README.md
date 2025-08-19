# Gaps Facilitator

A Flask web application for facilitating gap analysis using AI. This app provides an interactive board interface for organizing thoughts into quadrants (Status, Goal, Analysis, Plan) with AI-powered conversation and classification features.

## Features

- **Interactive Board Management**: Create and manage multiple boards with quadrant-based organization
- **AI-Powered Conversations**: Chat with AI to get insights and suggestions for your gap analysis
- **Thought Classification**: Automatically classify thoughts into appropriate quadrants using AI
- **Admin Controls**: Live-editable AI prompts for administrators
- **Multi-AI Support**: Works with both OpenAI and Google Gemini APIs
- **User Management**: Secure user authentication and admin privileges

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)
- OpenAI API key or Google Gemini API key

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd gaps_facilitator
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export AI_PROVIDER="openai"  # or "gemini"
   export OPENAI_API_KEY="your-openai-key"  # if using OpenAI
   export GEMINI_API_KEY="your-gemini-key"  # if using Gemini
   ```

5. **Initialize the database:**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

6. **Create an admin user:**
   ```bash
   python create_admin_user.py
   ```
   (Edit the script to set your desired admin username, email, and password)

7. **Run the application:**
   ```bash
   python app.py
   ```

   The app will be available at `http://localhost:5000`

### PythonAnywhere Deployment

1. **Upload all files** to your PythonAnywhere account
2. **Set up a virtual environment** in the PythonAnywhere console
3. **Install dependencies** from requirements.txt
4. **Set environment variables** in the WSGI configuration file
5. **Initialize the database** and create admin users
6. **Configure the web app** to point to your app.py file

## File Structure

```
gaps_facilitator/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── admin_prompt.py        # Admin blueprint for prompt editing
├── get_csrf_token.py      # CSRF token endpoint
├── openai_api.py          # OpenAI integration
├── gemini_api.py          # Google Gemini integration
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html        # Main application interface
│   └── prompt_editor.html # Admin prompt editor
├── prompts/              # AI prompt templates
│   └── prompts_modified.txt
├── static/               # Static assets (if any)
├── migrations/           # Database migrations
└── utils/                # Utility modules
```

## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python app.py`
3. Open [http://localhost:5000](http://localhost:5000) in your browser.

## Future Features
- Voice input
- Chatbot facilitator
- Persistent storage
