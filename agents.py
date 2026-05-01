#!/usr/bin/env python3
"""
CreditCoach AI — Multi-Agent System
Three specialized agents (ScoreSimulator, ActionPlan, PolicyExplainer) with an
orchestrator that classifies intent and routes to the right agent(s).

KEY FEATURE: Agents can delegate to each other via tool calls.
- ScoreSimulator can call → ask_action_plan_agent, ask_policy_agent
- ActionPlan can call → ask_score_simulator_agent
This follows the collaborative delegation pattern (like AskBenefits/AskDental
in watsonx Orchestrate).
"""
import json
from credit_engine import (
    TOOL_DEFINITIONS, TOOL_FUNCTIONS, find_member,
)

# ── Agent-specific tool sets ──

SCORE_TOOLS = [
    t for t in TOOL_DEFINITIONS
    if t["function"]["name"] in (
        "get_member_profile", "simulate_payment_impact",
        "simulate_timeline", "check_credit_health",
        "get_transaction_history",
    )
]

PLAN_TOOLS = [
    t for t in TOOL_DEFINITIONS
    if t["function"]["name"] in (
        "generate_action_plan", "get_member_profile",
        "get_transaction_history",
    )
]

# ── Inter-agent delegation tool definitions ──
# These let agents call each other as collaborators.

DELEGATE_TO_ACTION_PLAN = {
    "type": "function",
    "function": {
        "name": "ask_action_plan_agent",
        "description": (
            "Delegate to the ActionPlan Agent to generate a personalized credit "
            "improvement plan. Use this when the user wants advice on how to improve, "
            "or after showing a profile/simulation to proactively suggest next steps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "member_id": {"type": "string", "description": "Member ID to generate plan for"},
                "context": {"type": "string", "description": "Brief context about what the user asked"},
            },
            "required": ["member_id"],
        },
    },
}

DELEGATE_TO_POLICY = {
    "type": "function",
    "function": {
        "name": "ask_policy_agent",
        "description": (
            "Delegate to the PolicyExplainer Agent to answer questions about credit "
            "rights, disputes, FCRA, ECOA, debt collection rules, or consumer protections. "
            "Use this when the user asks about their legal rights or how to dispute errors."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The policy/rights question to answer"},
            },
            "required": ["question"],
        },
    },
}

DELEGATE_TO_SCORE_SIM = {
    "type": "function",
    "function": {
        "name": "ask_score_simulator_agent",
        "description": (
            "Delegate to the ScoreSimulator Agent to look up a member's credit profile, "
            "simulate score impacts, or generate timeline projections. Use this when you "
            "need score data to inform your action plan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "member_id": {"type": "string", "description": "Member ID to analyze"},
                "request": {"type": "string", "description": "What analysis to perform"},
            },
            "required": ["member_id"],
        },
    },
}

# Compose full tool sets with delegation capabilities
SCORE_SIMULATOR_TOOLS = SCORE_TOOLS + [DELEGATE_TO_ACTION_PLAN, DELEGATE_TO_POLICY]
ACTION_PLAN_TOOLS = PLAN_TOOLS + [DELEGATE_TO_SCORE_SIM]


def _parse_tool_args(raw):
    """Granite-4 sometimes double-encodes tool-call arguments as JSON-in-JSON.
    Unwrap until we get a dict, or fall back to wrapping a bare value as member_id."""
    args = raw
    for _ in range(3):
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError):
                break
        else:
            break
    if isinstance(args, dict):
        return args
    if args:
        return {"member_id": str(args)}
    return {}
# PolicyExplainer uses RAG only (no tool calling)

# ── Agent system prompts ──

AGENT_PROMPTS = {
    "score_simulator": (
        "You are the ScoreSimulator Agent, part of CreditCoach AI (IBM watsonx.ai).\n\n"
        "ROLE: Analyze credit profiles and simulate score impacts.\n\n"
        "TOOLS: get_member_profile, simulate_payment_impact, simulate_timeline, "
        "check_credit_health, get_transaction_history, ask_action_plan_agent, ask_policy_agent\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. You MUST call tools to get data. NEVER say you need more information — use the tools.\n"
        "2. If a member ID is mentioned (e.g. M0042, CUSTOM_xxx), IMMEDIATELY call get_member_profile with that ID.\n"
        "3. If no member ID is given, use member_id 'M0001' as a demo profile.\n"
        "4. NEVER refuse to act. ALWAYS call at least one tool.\n\n"
        "RESPONSE STYLE — BE SPECIFIC:\n"
        "- Reference EXACT account names, balances, and utilization percentages from the data\n"
        "- Say 'Your Visa Platinum is at 64% utilization ($320/$500)' NOT 'your utilization is high'\n"
        "- Say 'Paying $180 on your Visa brings it to 28% — below the 30% threshold' NOT 'pay down your cards'\n"
        "- Reference the key_observations from the profile — they flag the most important issues\n"
        "- Use FICO weights: Payment History 35%, Utilization 30%, Age 15%, Mix 10%, Inquiries 10%\n"
        "- When showing timelines, explain WHAT causes each path ('6 on-time payments' vs '2 missed payments')\n\n"
        "TONE: Encouraging, never judgmental. Plain language. Like a smart friend who happens to know credit.\n"
        "DELEGATION: Use ask_action_plan_agent for improvement plans. Use ask_policy_agent for rights questions.\n"
        "ALWAYS call tools — never guess numbers."
    ),
    "action_plan": (
        "You are the ActionPlan Agent, part of CreditCoach AI (IBM watsonx.ai).\n\n"
        "ROLE: Generate personalized, step-by-step credit improvement plans.\n\n"
        "TOOLS: generate_action_plan, get_member_profile, get_transaction_history, ask_score_simulator_agent\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. You MUST call tools to get data. NEVER say you need more information — use the tools.\n"
        "2. If a member ID is mentioned (e.g. M0042, CUSTOM_xxx), IMMEDIATELY call get_member_profile with that ID.\n"
        "3. If no member ID is given, use member_id 'M0001' as a demo profile.\n"
        "4. NEVER refuse to act. ALWAYS call at least one tool.\n"
        "5. After getting the profile, call generate_action_plan to create the plan.\n\n"
        "RESPONSE STYLE — BE SPECIFIC:\n"
        "- Reference EXACT account names and dollar amounts: 'Pay $180 on your Visa Platinum this month'\n"
        "- Give SPECIFIC timelines: 'If you do this for 3 months, expect +25-40 points by June'\n"
        "- Explain WHY each step matters with FICO percentages\n"
        "- For each step, give the estimated point impact range\n"
        "- Mention the transaction history if relevant: 'You've been late twice on your Auto Loan — set up autopay TODAY'\n"
        "- Call get_transaction_history to see recent payment patterns when creating plans\n\n"
        "TONE: Like a coach — direct, encouraging, actionable. No vague platitudes.\n"
        "DELEGATION: Use ask_score_simulator_agent if you need score projections."
    ),
    "policy_explainer": (
        "You are the PolicyExplainer Agent, part of the CreditCoach AI multi-agent system "
        "powered by IBM watsonx.ai.\n\n"
        "ROLE: Explain consumer credit rights, protections, and dispute processes.\n\n"
        "CAPABILITIES:\n"
        "- Answer questions about FCRA, ECOA, FDCPA, and other consumer protection laws\n"
        "- Guide users through the credit dispute process step by step\n"
        "- Explain medical debt protections, student loan rules, credit freezes\n"
        "- Help users understand their rights with debt collectors\n\n"
        "RULES:\n"
        "1. Use the RETRIEVED KNOWLEDGE BASE CONTEXT below to provide accurate answers.\n"
        "2. Always cite the relevant law or regulation by name.\n"
        "3. Use plain language a first-time credit user would understand.\n"
        "4. If the context doesn't cover the question, say so honestly.\n\n"
        "{rag_context}"
    ),
}

# ── Intent Classification (fixed) ──

INTENT_KEYWORDS = {
    "policy_explainer": [
        "rights", "right", "dispute", "fcra", "ecoa", "fdcpa", "law", "legal",
        "protection", "protect", "collection agency", "collector", "freeze",
        "fraud alert", "medical debt", "medical bill", "student loan protection",
        "report error", "error on my report", "complaint", "discrimination",
        "denied credit", "adverse action", "identity theft", "credit bureau",
        "equifax", "experian", "transunion", "cfpb", "fair credit",
    ],
    "action_plan": [
        "plan", "improve", "action", "steps", "goal", "target", "reach",
        "get to", "raise my", "boost", "increase my score", "better score",
        "what should i do", "advice", "recommend", "strategy",
        "fix my credit", "build credit", "rebuild",
    ],
    "score_simulator": [
        "profile", "score", "simulate", "what if", "what happens",
        "miss payment", "pay down", "impact", "timeline", "projection",
        "path", "scenario", "member", "m00", "check", "health", "grade",
        "max out", "close", "open new", "utilization", "show me",
    ],
}


def classify_intent(message):
    """Route user message to the best-fit agent(s)."""
    low = " " + message.lower() + " "
    scores = {}
    for agent, keywords in INTENT_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in low:
                # Exact word boundary match gets 2 points, substring gets 1
                score += 2 if f" {kw} " in low else 1
        scores[agent] = score

    if all(v == 0 for v in scores.values()):
        return ["score_simulator"]  # default

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    primary = ranked[0]
    agents = [primary[0]]

    # Add secondary agent if it scored >=50% of primary and > 0
    if len(ranked) > 1 and ranked[1][1] > 0 and ranked[1][1] >= primary[1] * 0.5:
        agents.append(ranked[1][0])

    return agents


# ── Orchestrator ──

AGENT_LABELS = {
    "score_simulator": "ScoreSimulator Agent",
    "action_plan": "ActionPlan Agent",
    "policy_explainer": "PolicyExplainer Agent",
}


class MultiAgentOrchestrator:
    """Routes user messages to specialized agents and collects structured results.
    Supports inter-agent delegation: agents can call each other via tool calls."""

    def __init__(self, model, rag_engine):
        self.model = model
        self.rag = rag_engine

    def run(self, user_message, conversation_history):
        agents_used = classify_intent(user_message)
        results = []
        all_viz = []
        all_tools = []

        for agent_name in agents_used:
            r = self._run_agent(agent_name, user_message, conversation_history)
            results.append(r)
            all_viz.extend(r.get("visualizations", []))
            all_tools.extend(r.get("tools_called", []))

        if len(results) == 1:
            reply = results[0]["reply"]
        else:
            reply = self._synthesize(results, agents_used)

        # Final safety net: strip any leaked tool-call JSON
        reply = self._strip_tool_json(reply)

        # Build delegation trace for UI
        delegation_trace = []
        for r in results:
            if r.get("delegation_trace"):
                delegation_trace.extend(r["delegation_trace"])

        return {
            "reply": reply,
            "agents_used": [AGENT_LABELS.get(a, a) for a in agents_used],
            "tools_called": all_tools,
            "visualizations": all_viz,
            "delegation_trace": delegation_trace,
        }

    # ── Agent dispatchers ──

    def _run_agent(self, name, msg, history):
        if name == "score_simulator":
            return self._exec_with_tools(
                AGENT_PROMPTS["score_simulator"], SCORE_SIMULATOR_TOOLS, msg, history)
        if name == "action_plan":
            return self._exec_with_tools(
                AGENT_PROMPTS["action_plan"], ACTION_PLAN_TOOLS, msg, history)
        if name == "policy_explainer":
            return self._exec_policy(msg, history)
        return {"reply": "", "tools_called": [], "visualizations": []}

    # ── Tool-calling agents (Score + Action) with inter-agent delegation ──

    def _exec_with_tools(self, system, tools, user_msg, history):
        messages = [{"role": "system", "content": system}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_msg})

        tools_called = []
        visualizations = []
        delegated_agents = []
        reply = ""

        # Agentic loop — let the model chain multiple tool calls before answering.
        for _ in range(4):
            resp = self.model.chat(messages=messages, tools=tools)
            choice = resp["choices"][0]
            tcs = choice["message"].get("tool_calls")

            if not (choice.get("finish_reason") == "tool_calls" or tcs):
                reply = choice["message"].get("content") or ""
                # Fallback: some models output tool calls as text JSON
                reply, _, _ = self._try_parse_text_tools(reply, tools_called, visualizations)
                break

            messages.append(choice["message"])
            for tc in tcs or []:
                fn = tc["function"]["name"]
                args = _parse_tool_args(tc["function"]["arguments"])
                tools_called.append(fn)

                if fn == "ask_action_plan_agent":
                    delegated_agents.append("ActionPlan Agent")
                    result = self._delegate_action_plan(args, visualizations)
                elif fn == "ask_policy_agent":
                    delegated_agents.append("PolicyExplainer Agent")
                    result = self._delegate_policy(args, visualizations)
                elif fn == "ask_score_simulator_agent":
                    delegated_agents.append("ScoreSimulator Agent")
                    result = self._delegate_score_sim(args, visualizations)
                elif fn in TOOL_FUNCTIONS:
                    result = TOOL_FUNCTIONS[fn](args)
                    self._collect_viz(fn, args, result, visualizations)
                else:
                    result = {"error": f"Unknown tool: {fn}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, indent=2) if isinstance(result, dict) else str(result),
                })

        # Append delegated agent names to tools_called for UI visibility
        tools_called.extend([f"delegated → {a}" for a in delegated_agents])

        # Build delegation trace
        delegation_trace = []
        for fn in tools_called:
            if fn.startswith("delegated"):
                continue
            if fn in ("ask_action_plan_agent", "ask_policy_agent", "ask_score_simulator_agent"):
                target = {"ask_action_plan_agent": "ActionPlan Agent",
                          "ask_policy_agent": "PolicyExplainer Agent",
                          "ask_score_simulator_agent": "ScoreSimulator Agent"}[fn]
                delegation_trace.append({"from": system[:40].strip(), "to": target, "tool": fn})
            else:
                delegation_trace.append({"tool": fn, "type": "tool_call"})

        # Strip any leaked tool-call JSON from the reply text
        reply = self._strip_tool_json(reply)

        return {"reply": reply, "tools_called": tools_called, "visualizations": visualizations,
                "delegation_trace": delegation_trace}

    # ── Strip leaked tool-call JSON from reply text ──

    def _strip_tool_json(self, reply):
        """Remove any tool-call / agent-delegation JSON or bracket markers that leaked into the reply."""
        if not reply:
            return reply
        import re
        # Match objects like {"name":"ask_...", "arguments":{...}} or
        # {"arguments":{...}, "name":"ask_..."} optionally wrapped in [ ]
        tool_json_patterns = [
            r'\[?\s*\{\s*"(?:name|action|function)"\s*:\s*"(?:ask_|get_|simulate_|search_|check_|generate_)\w+"\s*,\s*"(?:arguments|args)"\s*:\s*\{[^}]*\}\s*\}\s*\]?',
            r'\[?\s*\{\s*"(?:arguments|args)"\s*:\s*\{[^}]*\}\s*,\s*"(?:name|action|function)"\s*:\s*"(?:ask_|get_|simulate_|search_|check_|generate_)\w+"\s*\}\s*\]?',
        ]
        # Match bracket-style markers like [Call to ask_score_simulator_agent], [get_member_profile...], etc.
        bracket_patterns = [
            r'\[(?:Call(?:ing)?(?:\s+to)?|Calling|Using|Invoking|Tool(?:\s+call)?)\s*:?\s*\w+(?:_\w+)*(?:\s*\([^)]*\))?\s*\.{0,3}\]',
            r'\[(?:ask_|get_|simulate_|search_|check_|generate_)\w+(?:\s*\([^)]*\))?(?:\s*\.{2,})?\]',
            r'\[(?:ask_|get_|simulate_|search_|check_|generate_)\w+[^\]]*\]',
        ]
        for p in tool_json_patterns + bracket_patterns:
            reply = re.sub(p, '', reply, flags=re.DOTALL | re.IGNORECASE)
        # Clean up leftover whitespace
        reply = re.sub(r'\n{3,}', '\n\n', reply).strip()
        return reply

    # ── Fallback: parse tool calls from text when model doesn't use API ──

    def _try_parse_text_tools(self, reply, tools_called, visualizations):
        """If the model outputs tool call JSON as text, parse and execute it."""
        if not reply:
            return reply, tools_called, visualizations
        import re

        # Try to find any JSON with a "name"/"action"/"function" key
        patterns = [
            r'\{\s*"name"\s*:\s*"(?P<fn>\w+)"\s*,\s*"arguments"\s*:\s*(?P<args>\{[^}]*\})\s*\}',
            r'\{\s*"action"\s*:\s*"(?P<fn>\w+)"\s*,\s*"arguments"\s*:\s*(?P<args>\{[^}]*\})\s*\}',
            r'\{\s*"function"\s*:\s*"(?P<fn>\w+)"\s*,\s*"arguments"\s*:\s*(?P<args>\{[^}]*\})\s*\}',
            r'\{\s*"name"\s*:\s*"(?P<fn>\w+)"\s*,\s*"args"\s*:\s*(?P<args>\{[^}]*\})\s*\}',
            # arguments/args before name (reversed key order)
            r'\{\s*"arguments"\s*:\s*(?P<args>\{[^}]*\})\s*,\s*"name"\s*:\s*"(?P<fn>\w+)"\s*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, reply, re.DOTALL)
            if not match:
                continue
            fn_name = match.group("fn")
            try:
                fn_args = json.loads(match.group("args"))
            except json.JSONDecodeError:
                continue

            result = None

            # Handle credit engine tools
            if fn_name in TOOL_FUNCTIONS:
                tools_called.append(fn_name)
                result = TOOL_FUNCTIONS[fn_name](fn_args)
                self._collect_viz(fn_name, fn_args, result, visualizations)

            # Handle delegation tools
            elif fn_name == "ask_action_plan_agent":
                tools_called.append("ask_action_plan_agent")
                tools_called.append("delegated → ActionPlan Agent")
                result = self._delegate_action_plan(fn_args, visualizations)
            elif fn_name == "ask_policy_agent":
                tools_called.append("ask_policy_agent")
                tools_called.append("delegated → PolicyExplainer Agent")
                result = self._delegate_policy(fn_args, visualizations)
            elif fn_name == "ask_score_simulator_agent":
                tools_called.append("ask_score_simulator_agent")
                tools_called.append("delegated → ScoreSimulator Agent")
                result = self._delegate_score_sim(fn_args, visualizations)
            else:
                continue

            # Re-call the model with the tool result for a proper response
            messages = [
                {"role": "system", "content": (
                    "You are CreditCoach AI. You just called a tool and got a result. "
                    "Use the data below to give a helpful, specific, jargon-free response. "
                    "Reference specific account names, dollar amounts, and percentages from the data. "
                    "Do NOT output any JSON or tool calls — just give a clear explanation."
                )},
                {"role": "user", "content": f"Tool '{fn_name}' returned:\n\n{json.dumps(result, indent=2)[:3000]}"},
            ]
            resp = self.model.chat(messages=messages)
            reply = resp["choices"][0]["message"]["content"]
            return reply, tools_called, visualizations

        return reply, tools_called, visualizations

    # ── Inter-agent delegation handlers ──

    def _delegate_action_plan(self, args, viz_list):
        """ScoreSimulator delegates to ActionPlan Agent."""
        member_id = args.get("member_id", "")
        from credit_engine import generate_action_plan, get_member_profile
        plan = generate_action_plan(member_id)
        if not plan.get("error"):
            viz_list.append({"type": "action_plan", "data": plan})
        return plan

    def _delegate_policy(self, args, viz_list):
        """ScoreSimulator delegates to PolicyExplainer Agent (uses RAG)."""
        question = args.get("question", "")
        rag_ctx = self.rag.get_context(question, top_k=3)
        rag_results = self.rag.search(question, top_k=3)
        if rag_results:
            viz_list.append({"type": "rag_sources", "data": rag_results})
        # Run a mini policy agent call
        system = AGENT_PROMPTS["policy_explainer"].replace("{rag_context}", rag_ctx)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
        resp = self.model.chat(messages=messages)
        return {"policy_response": resp["choices"][0]["message"]["content"]}

    def _delegate_score_sim(self, args, viz_list):
        """ActionPlan delegates to ScoreSimulator Agent."""
        member_id = args.get("member_id", "")
        from credit_engine import get_member_profile, simulate_timeline
        profile = get_member_profile(member_id)
        timeline = simulate_timeline(member_id)
        if not profile.get("error"):
            raw = find_member(member_id)
            if raw:
                viz_list.append({"type": "profile", "data": {
                    "member_name": raw["member_name"],
                    "estimated_fico_score": raw["estimated_fico_score"],
                    "credit_tier": raw["credit_tier"],
                    "payment_history_ontime_pct": raw["payment_history_ontime_pct"],
                    "credit_utilization_pct": raw["credit_utilization_pct"],
                    "avg_account_age_months": raw["avg_account_age_months"],
                    "credit_mix": raw["credit_mix"],
                    "hard_inquiries_last_12mo": raw["hard_inquiries_last_12mo"],
                    "annual_income": raw["annual_income"],
                    "total_debt": raw["total_debt"],
                    "number_of_accounts": raw["number_of_accounts"],
                    "has_collections": raw["has_collections"],
                }})
        if not timeline.get("error"):
            viz_list.append({"type": "timeline", "data": timeline})
        return {"profile": profile, "timeline": timeline}

    # ── Policy agent (RAG, no credit-engine tools) ──

    def _exec_policy(self, user_msg, history):
        rag_ctx = self.rag.get_context(user_msg, top_k=3)
        system = AGENT_PROMPTS["policy_explainer"].replace("{rag_context}", rag_ctx)

        messages = [{"role": "system", "content": system}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_msg})

        resp = self.model.chat(messages=messages)
        reply = resp["choices"][0]["message"]["content"]

        rag_results = self.rag.search(user_msg, top_k=3)
        viz = [{"type": "rag_sources", "data": rag_results}] if rag_results else []

        return {
            "reply": reply,
            "tools_called": ["search_knowledge_base (RAG)"],
            "visualizations": viz,
        }

    # ── Visualization collector ──

    @staticmethod
    def _collect_viz(fn_name, fn_args, result, viz_list):
        if not result or result.get("error"):
            return
        if fn_name == "simulate_timeline":
            viz_list.append({"type": "timeline", "data": result})
        elif fn_name == "get_member_profile":
            raw = find_member(fn_args.get("member_id", ""))
            if raw:
                viz_list.append({"type": "profile", "data": {
                    "member_name": raw["member_name"],
                    "estimated_fico_score": raw["estimated_fico_score"],
                    "credit_tier": raw["credit_tier"],
                    "payment_history_ontime_pct": raw["payment_history_ontime_pct"],
                    "credit_utilization_pct": raw["credit_utilization_pct"],
                    "avg_account_age_months": raw["avg_account_age_months"],
                    "credit_mix": raw["credit_mix"],
                    "hard_inquiries_last_12mo": raw["hard_inquiries_last_12mo"],
                    "annual_income": raw["annual_income"],
                    "total_debt": raw["total_debt"],
                    "number_of_accounts": raw["number_of_accounts"],
                    "has_collections": raw["has_collections"],
                }})
                # Per-account utilization breakdown
                card_breakdown = []
                for a in raw.get("accounts", []):
                    if a["account_type"] == "credit_card" and a["credit_limit_or_original"] > 0:
                        card_breakdown.append({
                            "name": a["account_name"],
                            "balance": a["current_balance"],
                            "limit": a["credit_limit_or_original"],
                            "utilization": round(a["current_balance"] / a["credit_limit_or_original"] * 100, 1),
                        })
                if card_breakdown:
                    viz_list.append({"type": "account_breakdown", "data": card_breakdown})
        elif fn_name == "check_credit_health":
            viz_list.append({"type": "health", "data": result})
        elif fn_name == "generate_action_plan":
            viz_list.append({"type": "action_plan", "data": result})
        elif fn_name == "simulate_payment_impact":
            viz_list.append({"type": "impact", "data": result})

    # ── Multi-agent synthesis ──

    @staticmethod
    def _synthesize(results, agents):
        labels = {"score_simulator": "Score Analysis", "action_plan": "Action Plan",
                  "policy_explainer": "Policy & Rights"}
        parts = []
        for res, agent in zip(results, agents):
            parts.append(f"**[{labels.get(agent, agent)}]**\n{res['reply']}")
        return "\n\n---\n\n".join(parts)
