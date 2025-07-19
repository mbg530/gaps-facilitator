import openai
from models import ConversationTurn, db
from sqlalchemy import asc

def summarize_conversation(board_id, keep_last_n=6):
    """
    Summarize all but the last N turns for a board and store as a ConversationTurn with role='summary'.
    Deletes the summarized turns.
    Returns the summary string.
    """
    # Get all turns except last N
    all_turns = (
        ConversationTurn.query
        .filter_by(board_id=board_id)
        .order_by(asc(ConversationTurn.timestamp))
        .all()
    )
    if len(all_turns) <= keep_last_n:
        return None  # Nothing to summarize
    to_summarize = all_turns[:-keep_last_n]
    # Compose text for summarization
    convo_text = "\n".join(f"{t.role}: {t.content}" for t in to_summarize)
    prompt = (
        "Summarize the following conversation for context. "
        "Focus on key issues, goals, and progress. Be concise.\n\n"
        f"{convo_text}"
    )
    # Call OpenAI (assumes API key in env)
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2,
        max_tokens=200
    )
    summary = response.choices[0].message.content.strip()
    # Store summary turn
    db.session.add(ConversationTurn(
        board_id=board_id,
        user_id=None,
        role='summary',
        content=summary
    ))
    # Delete summarized turns
    for t in to_summarize:
        db.session.delete(t)
    db.session.commit()
    return summary
