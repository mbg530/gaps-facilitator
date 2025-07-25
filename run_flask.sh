#!/bin/bash
# Experimental Environment - Rule-Based + LLM Hybrid Categorization
source venv_experimental/bin/activate
export FLASK_APP=app.py
export FLASK_ENV=development
# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi
export AI_PROVIDER=openai  # Use openai or gemini with hybrid categorization
export OPENAI_MODEL=gpt-4-turbo
export SHOW_JSON_WARNING=false
export APP_VERSION='072425 0707'
flask run --debug --port=5001
