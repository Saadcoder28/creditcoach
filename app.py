#!/usr/bin/env python3
"""
CreditCoach AI — Main Application
Multi-agent credit health system powered by IBM watsonx.ai Granite models.
Features: RAG knowledge retrieval, 3 specialized agents, rich visualizations.
Run:  python app.py
Open: http://localhost:8080
"""
import os, sys, json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from rag_engine import RAGEngine
from agents import MultiAgentOrchestrator

load_dotenv()

# ── Validate credentials at startup ──
API_KEY    = os.getenv("WATSONX_API_KEY", "").strip()
PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "").strip()
URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
MODEL_ID   = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")

if not API_KEY or not PROJECT_ID:
    print("\n  ERROR: Missing WATSONX_API_KEY or WATSONX_PROJECT_ID in .env")
    print("  Please fill in your IBM watsonx.ai credentials and restart.\n")
    sys.exit(1)

credentials = Credentials(url=URL, api_key=API_KEY)
model = ModelInference(
    model_id=MODEL_ID,
    credentials=credentials,
    project_id=PROJECT_ID,
    params={"max_tokens": 1500, "temperature": 0.3},
)

# ── RAG Engine (vector search over knowledge docs) ──
print("\n  Initializing RAG Engine...")
rag = RAGEngine(credentials=credentials, project_id=PROJECT_ID)

# ── Multi-Agent Orchestrator ──
print("  Initializing Multi-Agent Orchestrator...")
orchestrator = MultiAgentOrchestrator(model, rag)

# ── Flask app ──
app = Flask(__name__)
conversations = {}
MAX_MSG_LEN = 2000
MAX_SESSIONS = 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"reply": "Invalid request.", "agents_used": [],
                        "tools_called": [], "visualizations": []}), 400

    user_msg = (data.get("message") or "").strip()
    session_id = data.get("session_id", "default")

    if not user_msg:
        return jsonify({"reply": "Please enter a message.", "agents_used": [],
                        "tools_called": [], "visualizations": []})

    if len(user_msg) > MAX_MSG_LEN:
        user_msg = user_msg[:MAX_MSG_LEN]

    # Session management with cap
    if session_id not in conversations:
        if len(conversations) >= MAX_SESSIONS:
            oldest = next(iter(conversations))
            del conversations[oldest]
        conversations[session_id] = []

    try:
        result = orchestrator.run(user_msg, conversations[session_id])

        conversations[session_id].append({"role": "user", "content": user_msg})
        conversations[session_id].append({"role": "assistant", "content": result["reply"]})
        if len(conversations[session_id]) > 20:
            conversations[session_id] = conversations[session_id][-20:]

        return jsonify({
            "reply":          result["reply"],
            "agents_used":    result["agents_used"],
            "tools_called":   result["tools_called"],
            "visualizations": result["visualizations"],
            "delegation_trace": result.get("delegation_trace", []),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "reply": f"Something went wrong: {str(e)}. Please try again.",
            "agents_used": [],
            "tools_called": [],
            "visualizations": [],
        }), 500


@app.route("/analyze", methods=["POST"])
def analyze():
    """Create a custom profile from form data, run all tools, return visualizations + chat."""
    from credit_engine import create_custom_profile, get_member_profile, check_credit_health, \
        generate_action_plan, simulate_timeline, find_member
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    member_id = create_custom_profile(data)
    session_id = data.get("session_id", "default")

    # Run all tools against the custom profile
    profile = get_member_profile(member_id)
    health = check_credit_health(member_id)
    plan = generate_action_plan(member_id)
    timeline = simulate_timeline(member_id)

    # Build visualizations
    raw = find_member(member_id)
    visualizations = []
    if raw:
        visualizations.append({"type": "profile", "data": {
            "member_name": raw["member_name"],
            "estimated_fico_score": raw["estimated_fico_score"],
            "credit_tier": raw["credit_tier"],
            "payment_history_ontime_pct": raw["payment_history_ontime_pct"],
            "credit_utilization_pct": raw["credit_utilization_pct"],
            "avg_account_age_months": raw["avg_account_age_months"],
            "credit_mix": raw["credit_mix"],
            "hard_inquiries_last_12mo": raw["hard_inquiries_last_12mo"],
            "annual_income": raw.get("annual_income", 0),
            "total_debt": raw["total_debt"],
            "number_of_accounts": raw["number_of_accounts"],
            "has_collections": raw["has_collections"],
        }})
    # Per-account utilization breakdown for credit cards
    card_breakdown = []
    for a in raw.get("accounts", []) if raw else []:
        if a["account_type"] == "credit_card" and a["credit_limit_or_original"] > 0:
            card_breakdown.append({
                "name": a["account_name"],
                "balance": a["current_balance"],
                "limit": a["credit_limit_or_original"],
                "utilization": round(a["current_balance"] / a["credit_limit_or_original"] * 100, 1),
            })
    if card_breakdown:
        visualizations.append({"type": "account_breakdown", "data": card_breakdown})
    if not health.get("error"):
        visualizations.append({"type": "health", "data": health})
    if not plan.get("error"):
        visualizations.append({"type": "action_plan", "data": plan})
    if not timeline.get("error"):
        visualizations.append({"type": "timeline", "data": timeline})

    # Build a prompt for the AI to give a conversational response
    prompt = (
        f"I just submitted my credit profile for analysis. My member ID is {member_id}. "
        f"Here is the data the tools returned:\n\n"
        f"Profile: {json.dumps(profile, indent=2)[:1500]}\n\n"
        f"Health: {json.dumps(health, indent=2)[:500]}\n\n"
        f"Action Plan: {json.dumps(plan, indent=2)[:800]}\n\n"
        f"Please give me a warm, personalized summary of my credit situation. "
        f"Reference my SPECIFIC accounts by name, mention exact dollar amounts I should pay, "
        f"and explain what my biggest opportunity is. Keep it conversational and encouraging."
    )

    # Session management
    if session_id not in conversations:
        if len(conversations) >= MAX_SESSIONS:
            oldest = next(iter(conversations))
            del conversations[oldest]
        conversations[session_id] = []

    try:
        result = orchestrator.run(prompt, conversations[session_id])
        conversations[session_id].append({"role": "user", "content": prompt})
        conversations[session_id].append({"role": "assistant", "content": result["reply"]})

        return jsonify({
            "reply": result["reply"],
            "agents_used": result["agents_used"],
            "tools_called": result["tools_called"],
            "visualizations": visualizations + result.get("visualizations", []),
            "member_id": member_id,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "reply": f"Analysis complete but AI summary failed: {str(e)}",
            "agents_used": [],
            "tools_called": [],
            "visualizations": visualizations,
            "member_id": member_id,
        })


@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    conversations.pop(session_id, None)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("=" * 60)
    print("  CreditCoach AI — Multi-Agent Credit Health System")
    print(f"  Model : {MODEL_ID}")
    print(f"  Agents: ScoreSimulator | ActionPlan | PolicyExplainer")
    print(f"  RAG   : {'watsonx embeddings' if rag.use_watsonx else 'TF-IDF fallback'}")
    print("=" * 60)
    port = int(os.environ.get("PORT", 8080))
    print(f"  Open http://localhost:{port} in your browser")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
