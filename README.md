# CreditCoach AI — Multi-Agent Credit Health System
## IBM SkillsBuild AI Experiential Learning Lab 2026 | Banking Challenge

### The Problem
Over **26 million Americans are credit invisible** — they have no credit score at all. Millions more are stuck with low scores, locked out of fair lending, housing, and employment. Without guidance, they fall prey to predatory lenders, make mistakes that damage their score for years, and don't know their legal rights.

### Our Solution
CreditCoach AI is a **multi-agent agentic system** that gives every consumer a personal credit advisor — powered by IBM watsonx.ai. Three specialized AI agents collaborate to analyze credit profiles, simulate financial decisions, build personalized improvement plans, and explain consumer rights in plain language.

**No jargon. No judgment. Just a clear path forward.**

### Key Features
- **3 Specialized AI Agents** that route, delegate, and collaborate:
  - **ScoreSimulator** — Analyzes profiles, simulates score impacts, projects 12-month timelines
  - **ActionPlan** — Generates prioritized step-by-step plans with exact dollar amounts
  - **PolicyExplainer** — Explains FCRA, ECOA, FDCPA rights using RAG retrieval
- **Inter-Agent Delegation** — Agents call each other via tool calls (e.g., ActionPlan delegates to ScoreSimulator for projections)
- **6 Credit Analysis Tools** — LLM-invoked functions for profile analysis, impact simulation, timeline projection, action plans, health checkups, and transaction history
- **RAG Knowledge Retrieval** — 153 chunks across 5 documents (FICO guide, consumer rights, building credit from zero, credit strategies, dispute templates) embedded with IBM watsonx embeddings
- **"Analyze My Credit" Form** — Users enter their real accounts (type, limit, balance, status) and get full visualizations with per-account analysis and exact payoff targets
- **Zero-Credit Guidance** — Dedicated flow for credit-invisible users: secured cards, authorized users, pre-qualification, rejection avoidance
- **Rich Visualizations** — 7 chart types: score gauge, FICO factor bars, per-account utilization breakdown, timeline projections, health grades, action plans, impact simulations
- **4 Guided Journeys** — "New to Credit," "Score Won't Budge," "Go Higher," and custom analysis

### IBM Technology Used
| Technology | Usage |
|---|---|
| **IBM watsonx.ai** | Granite 3 8B Instruct — multi-agent reasoning, tool calling, response generation |
| **IBM watsonx Embeddings** | slate-125m-english-rtrvr-v2 — semantic search over 153 RAG chunks |
| **Tool Calling API** | 6 structured tools + 3 inter-agent delegation tools invoked by the LLM |

### Architecture
```
User (Browser)
    |
    v
Flask Web UI ──> Intent Classifier ──> Agent Router
                                            |
                    ┌───────────────────────┼───────────────────────┐
                    v                       v                       v
            ScoreSimulator           ActionPlan             PolicyExplainer
            (watsonx + tools)        (watsonx + tools)      (watsonx + RAG)
                    |                       |                       |
            ┌───────┴───────┐        ┌──────┴──────┐         Knowledge Base
            v               v        v             v          (153 chunks)
      Credit Engine    Can delegate   Can delegate
      (6 tools)        to Policy      to ScoreSim
            |
    200 Synthetic Profiles
```

### Measurable Impact
- **Score Projections**: Shows exact point improvements (e.g., "Pay $1,220 on Mastercard Gold → +35 pts")
- **Zero to 670+**: Credit-invisible users get a month-by-month plan to build a score in 6-12 months
- **Rejection Prevention**: Guides new users to pre-qualify before applying, avoiding hard inquiries that damage thin files
- **Rights Awareness**: RAG-grounded legal guidance helps consumers dispute errors and negotiate with collectors

### Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Edit .env with your IBM watsonx.ai credentials
#    WATSONX_API_KEY=your_key
#    WATSONX_PROJECT_ID=your_project_id

# 3. Run the app
python app.py

# 4. Open browser
open http://localhost:8080
```

### Files
| File | Purpose |
|---|---|
| `app.py` | Flask app + watsonx.ai integration + `/chat` and `/analyze` endpoints |
| `agents.py` | Multi-agent orchestrator: 3 agents, intent classification, inter-agent delegation |
| `credit_engine.py` | 6 credit analysis tools + FICO simulation logic + custom profile creation |
| `rag_engine.py` | RAG engine: watsonx embeddings + TF-IDF fallback, semantic chunking |
| `data/credit_profiles.json` | 200 synthetic consumer profiles (M0001-M0200) |
| `knowledge/` | 5 RAG documents (153 chunks): FICO guide, consumer rights, building from zero, strategies, dispute templates |
| `static/js/app.js` | Frontend: 4 guided journeys, 7 visualization types, dynamic account form |
| `static/css/style.css` | Responsive design system with IBM Plex typography |

### Dataset
200 synthetic consumer profiles spanning the full credit spectrum — from credit-invisible (score 0) to exceptional (800+). Each profile includes detailed accounts, payment history, utilization, and negative marks. All data is self-generated and compliant.

### Team
IBM SkillsBuild AI Experiential Learning Lab 2026
