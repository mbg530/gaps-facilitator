import openai
import os

# Set your OpenAI API key here or via environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "sk-..."

# Load prompt from a file
PROMPT_FILE = "minimal_gaps_prompt.txt"

if not os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "w") as f:
        f.write("""You are a helpful GAPS facilitator. Greet the user, offer a quick intro if they want it, then guide them to state their first problem or goal. Always keep the conversation focused on the GAPS process.\n\nUser: __FIRST_MESSAGE__\nAI: Welcome! I use the GAPS model to help clarify and solve problems. Would you like a quick intro to how it works, or are you already familiar with GAPS?\n""")

with open(PROMPT_FILE, "r") as f:
    system_prompt = f.read()

openai.api_key = OPENAI_API_KEY

conversation = []

print("Minimal GAPS Prompt Tester\nType 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.strip().lower() == "exit":
        break
    conversation.append({"role": "user", "content": user_input})
    # Build message history
    messages = [{"role": "system", "content": system_prompt}]
    for turn in conversation:
        messages.append(turn)
    # Call OpenAI ChatCompletion API
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # or "gpt-4" if you have access
        messages=messages,
        temperature=0.6,
        max_tokens=400
    )
    ai_reply = response.choices[0].message.content
    print(f"AI: {ai_reply}\n")
    conversation.append({"role": "assistant", "content": ai_reply})
