from models import ConversationTurn, Board
from sqlalchemy import desc

def get_recent_conversation(board_id, limit=8):
    """Fetch the last N conversation turns for a board, oldest to newest (excluding summaries)."""
    turns = (
        ConversationTurn.query
        .filter_by(board_id=board_id)
        .filter(ConversationTurn.role.in_(['user', 'assistant']))
        .order_by(desc(ConversationTurn.timestamp))
        .limit(limit)
        .all()
    )
    return list(reversed(turns))

def get_latest_summary(board_id):
    """Fetch the most recent summary turn for a board, or None."""
    return (
        ConversationTurn.query
        .filter_by(board_id=board_id, role='summary')
        .order_by(desc(ConversationTurn.timestamp))
        .first()
    )

def get_board_summary(board_id):
    """Build a compact summary string for the board/quadrant state."""
    board = Board.query.get(board_id)
    if not board:
        return "(No board found)"
    # You may want to customize this summary based on your actual Board/Thought schema
    status = []
    goal = []
    analysis = []
    plan = []
    for t in board.thoughts:
        if t.quadrant == 'status': status.append(t.content)
        elif t.quadrant == 'goal': goal.append(t.content)
        elif t.quadrant == 'analysis': analysis.append(t.content)
        elif t.quadrant == 'plan': plan.append(t.content)
    summary = (
        f"Status: {'; '.join(status) or 'None'}\n"
        f"Goal: {'; '.join(goal) or 'None'}\n"
        f"Analysis: {'; '.join(analysis) or 'None'}\n"
        f"Plan: {'; '.join(plan) or 'None'}"
    )
    return summary

def build_openai_prompt(board_id, user_input, system_prompt=None):
    """
    Assemble the prompt for OpenAI: system prompt, board summary, latest summary, recent conversation, and user input.
    Returns a list of messages (dicts with 'role' and 'content').
    """
    if not system_prompt:
        system_prompt = (
            "You are a helpful GAPS facilitator. "
            "When suggesting actions or recommendations, ALWAYS return your recommendations as a valid JSON object with an 'add_to_quadrant' array. "
            "Each item should have a 'quadrant' (one of 'status', 'goal', 'analysis', or 'plan') and a 'thought'. "
            "Example:\n"
            '{\n  "add_to_quadrant": [\n    {"quadrant": "goal", "thought": "Implement customer feedback loop"},\n    {"quadrant": "plan", "thought": "Assemble cross-functional AI team"}\n  ]\n}\n'
            "If you have other comments, you may provide them as plain text before or after the JSON, but always include the JSON block so the user can take action on your recommendations."
        )
    recent_msgs = get_recent_conversation(board_id)
    summary = get_board_summary(board_id)
    summary_turn = get_latest_summary(board_id)
    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Board summary:\n{summary}"},
    ]
    if summary_turn:
        prompt.append({"role": "user", "content": f"Conversation summary:\n{summary_turn.content}"})
    for msg in recent_msgs:
        prompt.append({"role": msg.role, "content": msg.content})
    prompt.append({"role": "user", "content": user_input})
    return prompt
