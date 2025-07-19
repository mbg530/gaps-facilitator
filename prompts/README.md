# Prompt File Pattern for GAPS Facilitator

## Overview
All AI prompts used by the GAPS Facilitator project are stored as plain text files in this `prompts/` directory. This approach ensures that prompt logic is easy to maintain, update, and extend—without modifying Python code.

## How It Works
- **Prompt Files:** Each AI endpoint or feature has a corresponding `.txt` file in this directory (e.g., `classify_thought.txt`, `conversational_facilitator.txt`, `suggest_solution.txt`, `interactive_gaps.txt`).
- **Placeholders:** Prompt files may contain placeholders (e.g., `<STATUS>`, `<GOAL>`, `{conversation_history}`) to be filled in by the backend code.
- **Loading and Filling:** The backend uses the `load_and_fill_prompt` utility function to load prompts and fill in placeholders with runtime data.

## Usage Pattern
1. **Create/Edit a Prompt File:**
   - Add your prompt template as a `.txt` file here.
   - Use clear placeholders for any dynamic content.
2. **In Python Code:**
   - Use `from openai_api import load_and_fill_prompt`.
   - Load and fill the prompt like this:
     ```python
     prompt = load_and_fill_prompt(
         'prompts/interactive_gaps.txt',
         STATUS='...', GOAL='...', ANALYSIS='...', PLAN='...', CONVERSATION='...', USER_INPUT='...'
     )
     ```

## Benefits
- **Maintainability:** Prompts can be updated without changing code.
- **Clarity:** All prompt logic is in one place.
- **Consistency:** All AI endpoints follow the same pattern.

## Adding a New Prompt
1. Create a new `.txt` file in this directory with your prompt template and placeholders as needed.
2. Use `load_and_fill_prompt` in your Python code to load and fill the template.

---

_This pattern is designed for clarity, maintainability, and easy collaboration between developers and prompt engineers._
