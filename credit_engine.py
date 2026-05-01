#!/usr/bin/env python3
"""
CreditCoach AI — Credit Engine
All credit score simulation, analysis, and action plan logic.
"""
import json, os

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "credit_profiles.json")
with open(DATA_PATH) as f:
    PROFILES = json.load(f)
PROFILES_BY_ID = {p["member_id"]: p for p in PROFILES}
PROFILES_BY_NAME = {p["member_name"].lower(): p for p in PROFILES}

CUSTOM_PROFILES = {}  # runtime custom profiles from the form

def find_member(mid):
    key = mid.strip()
    if key in CUSTOM_PROFILES: return CUSTOM_PROFILES[key]
    if key in PROFILES_BY_ID: return PROFILES_BY_ID[key]
    lo = key.lower()
    if lo in PROFILES_BY_NAME: return PROFILES_BY_NAME[lo]
    for n, p in PROFILES_BY_NAME.items():
        if lo in n: return p
    return None


def create_custom_profile(data):
    """Create a synthetic member profile from user-submitted form data.
    Returns the member_id assigned to the custom profile."""
    import time
    mid = f"CUSTOM_{int(time.time()) % 100000:05d}"
    accounts = []
    total_balance = 0
    total_limit = 0
    cc_balance = 0
    cc_limit = 0
    has_collections = False
    late_30 = 0
    late_60 = 0
    late_90 = 0

    type_counters = {}
    type_names = {
        "credit_card": ["Visa Platinum", "Mastercard Gold", "Discover It", "Amex Blue", "Capital One Quicksilver"],
        "auto_loan": ["Auto Loan", "Vehicle Financing"],
        "student_loan": ["Student Loan", "Education Loan"],
        "mortgage": ["Home Mortgage", "Housing Loan"],
        "personal_loan": ["Personal Loan", "Signature Loan"],
    }
    for acct in data.get("accounts", []):
        atype = acct.get("type", "credit_card")
        limit_val = float(acct.get("limit", 0) or 0)
        balance_val = float(acct.get("balance", 0) or 0)
        status_raw = acct.get("status", "current")
        # Map status
        status_map = {"current": "current", "30_late": "30_days_late", "60_late": "60_days_late",
                      "90_late": "90_days_late", "collection": "collections"}
        status = status_map.get(status_raw, "current")
        if status == "collections":
            has_collections = True
        if "30" in status: late_30 += 1
        if "60" in status: late_60 += 1
        if "90" in status: late_90 += 1

        idx = type_counters.get(atype, 0)
        type_counters[atype] = idx + 1
        names = type_names.get(atype, ["Account"])
        name = names[idx % len(names)]

        total_balance += balance_val
        total_limit += limit_val
        if atype == "credit_card":
            cc_balance += balance_val
            cc_limit += limit_val

        pmt = int(balance_val * 0.03) if atype == "credit_card" else int(balance_val / max(1, 48)) if limit_val > 0 else 0
        accounts.append({
            "account_type": atype,
            "account_name": name,
            "current_balance": int(balance_val),
            "credit_limit_or_original": int(limit_val),
            "monthly_payment": max(pmt, 25) if balance_val > 0 else 0,
            "status": status,
            "age_months": 18,  # default
        })

    score = int(data.get("score", 0) or 0) or 580
    pay_pct = float(data.get("payment_pct", 100) or 100)
    late_total = int(data.get("late_payments", 0) or 0)
    inq = int(data.get("inquiries", 0) or 0)
    util = round(cc_balance / max(cc_limit, 1) * 100, 1) if cc_limit > 0 else 0

    # Distribute late payments if form total > account-detected
    if late_total > (late_30 + late_60 + late_90):
        extra = late_total - (late_30 + late_60 + late_90)
        late_30 += extra

    # Determine credit mix
    types_present = set(a["account_type"] for a in accounts)
    has_revolving = "credit_card" in types_present
    has_installment = bool(types_present - {"credit_card"})
    if has_revolving and has_installment:
        mix = "credit_card_and_loan"
    elif has_revolving:
        mix = "credit_card_only"
    elif has_installment:
        mix = "loan_only"
    else:
        mix = "none"

    tier = "exceptional" if score >= 800 else "very_good" if score >= 740 else "good" if score >= 670 else "fair" if score >= 580 else "poor"

    profile = {
        "member_id": mid,
        "member_name": "You",
        "age": 30,
        "annual_income": 50000,
        "estimated_fico_score": score,
        "credit_tier": tier,
        "payment_history_ontime_pct": pay_pct,
        "late_payments_30day": late_30,
        "late_payments_60day": late_60,
        "late_payments_90day": late_90,
        "credit_utilization_pct": util,
        "avg_account_age_months": 18,
        "number_of_accounts": len(accounts),
        "credit_mix": mix,
        "hard_inquiries_last_12mo": inq,
        "total_debt": int(total_balance),
        "has_collections": has_collections,
        "has_bankruptcy": False,
        "accounts": accounts,
    }
    CUSTOM_PROFILES[mid] = profile
    return mid

def get_member_profile(member_id):
    m = find_member(member_id)
    if not m: return {"error": f"Member '{member_id}' not found."}
    # Per-account utilization
    accounts = []
    for a in m.get("accounts", []):
        acct = {
            "type": a["account_type"].replace("_", " "),
            "name": a["account_name"],
            "balance": f"${a['current_balance']:,}",
            "limit_or_original": f"${a['credit_limit_or_original']:,}",
            "age_months": a["age_months"],
            "monthly_payment": f"${a['monthly_payment']:,}",
            "status": a["status"].replace("_", " "),
        }
        if a["account_type"] == "credit_card" and a["credit_limit_or_original"] > 0:
            acct["utilization"] = f"{a['current_balance']/a['credit_limit_or_original']*100:.0f}%"
        accounts.append(acct)
    # Income-to-debt ratio
    dti = round(m["total_debt"] / max(m["annual_income"], 1) * 100, 1)
    return {
        "member_id": m["member_id"], "member_name": m["member_name"], "age": m["age"],
        "annual_income": f"${m['annual_income']:,}", "estimated_fico_score": m["estimated_fico_score"],
        "credit_tier": m["credit_tier"],
        "payment_history_ontime_pct": f"{m['payment_history_ontime_pct']}%",
        "late_payments_30day": m["late_payments_30day"],
        "late_payments_60day": m["late_payments_60day"],
        "late_payments_90day": m["late_payments_90day"],
        "total_late_payments": m["late_payments_30day"] + m["late_payments_60day"] + m["late_payments_90day"],
        "credit_utilization_pct": f"{m['credit_utilization_pct']}%",
        "avg_account_age_months": m["avg_account_age_months"],
        "oldest_account_age_months": max((a["age_months"] for a in m.get("accounts", [])), default=0),
        "newest_account_age_months": min((a["age_months"] for a in m.get("accounts", [])), default=0),
        "credit_mix": m["credit_mix"].replace("_", " "),
        "hard_inquiries_last_12mo": m["hard_inquiries_last_12mo"],
        "total_debt": f"${m['total_debt']:,}",
        "debt_to_income_ratio": f"{dti}%",
        "number_of_accounts": m["number_of_accounts"],
        "has_collections": m["has_collections"],
        "has_bankruptcy": m.get("has_bankruptcy", False),
        "accounts": accounts,
        "key_observations": _get_observations(m),
    }


def _get_observations(m):
    """Generate specific observations about the profile for the AI to use."""
    obs = []
    # No credit history at all
    if m["estimated_fico_score"] == 0 or m["number_of_accounts"] == 0:
        obs.append("NO CREDIT HISTORY: This person has no credit score yet — they are 'credit invisible.' They need to establish credit from scratch.")
        obs.append("FIRST STEP: Apply for a secured credit card ($200-500 deposit) or become an authorized user on a family member's card.")
        obs.append("AVOID REJECTION: Do NOT apply for regular credit cards — they will be denied and the hard inquiry will hurt when they do get a score.")
        obs.append("PRE-QUALIFY FIRST: Always use pre-qualification tools (Capital One, Discover) before applying to avoid unnecessary hard inquiries.")
        obs.append("TIMELINE: With a secured card used responsibly (under 10% utilization, autopay), they can build a 670+ score in 6-12 months.")
        return obs
    if m["payment_history_ontime_pct"] < 90:
        obs.append(f"CRITICAL: Payment history is only {m['payment_history_ontime_pct']}%. This is the #1 factor (35% of score). Every on-time payment matters.")
    if m["credit_utilization_pct"] > 50:
        obs.append(f"HIGH UTILIZATION: At {m['credit_utilization_pct']}%, this is severely hurting the score. Paying down to under 30% could add 30-60 points.")
    elif m["credit_utilization_pct"] > 30:
        obs.append(f"ELEVATED UTILIZATION: At {m['credit_utilization_pct']}%, getting below 30% would help. Below 10% is ideal.")
    if m["avg_account_age_months"] < 12:
        obs.append(f"THIN FILE: Average account age is only {m['avg_account_age_months']} months. Time is needed — avoid opening new accounts.")
    if m["has_collections"]:
        obs.append("COLLECTION ON FILE: This is a major negative mark. Consider pay-for-delete negotiation.")
    if m["hard_inquiries_last_12mo"] > 3:
        obs.append(f"TOO MANY INQUIRIES: {m['hard_inquiries_last_12mo']} hard pulls in 12 months. Stop applying for new credit.")
    # Check per-card utilization
    for a in m.get("accounts", []):
        if a["account_type"] == "credit_card" and a["credit_limit_or_original"] > 0:
            util = a["current_balance"] / a["credit_limit_or_original"] * 100
            if util > 70:
                obs.append(f"CARD '{a['account_name']}' is at {util:.0f}% utilization (${a['current_balance']:,}/${a['credit_limit_or_original']:,}). Pay this down first — highest impact.")
    if m["credit_mix"] in ("credit_card_only", "loan_only"):
        obs.append(f"LIMITED CREDIT MIX: Only {m['credit_mix'].replace('_',' ')}. Having both revolving and installment credit helps.")
    if not obs:
        obs.append("Profile looks solid. Focus on maintaining good habits and letting accounts age.")
    return obs


def get_transaction_history(member_id):
    """Generate synthetic recent transaction/payment history for a member."""
    import random, hashlib
    m = find_member(member_id)
    if not m: return {"error": f"Member '{member_id}' not found."}
    # Use member_id as seed for reproducibility
    seed = int(hashlib.md5(member_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    months = ["Jan 2026","Feb 2026","Mar 2026","Dec 2025","Nov 2025","Oct 2025"]
    history = []
    for a in m.get("accounts", []):
        acct_history = {"account": a["account_name"], "type": a["account_type"].replace("_"," "), "payments": []}
        for i, month in enumerate(months):
            if a["status"] in ("30_days_late","60_days_late","90_days_late") and i < 2:
                status = "LATE" if rng.random() < 0.6 else "On time"
            elif m["payment_history_ontime_pct"] < 85 and rng.random() < 0.15:
                status = "LATE"
            else:
                status = "On time"
            pmt = a["monthly_payment"]
            if a["account_type"] == "credit_card":
                spent = rng.randint(int(pmt * 0.5), int(pmt * 3)) if pmt > 0 else rng.randint(20, 200)
                acct_history["payments"].append({"month": month, "spent": f"${spent:,}", "paid": f"${pmt:,}", "status": status})
            else:
                acct_history["payments"].append({"month": month, "paid": f"${pmt:,}", "status": status})
        history.append(acct_history)
    return {
        "member_name": m["member_name"], "member_id": m["member_id"],
        "transaction_history": history,
        "summary": f"{len(history)} accounts, {len(months)} months of history shown"
    }

def simulate_payment_impact(member_id, action, amount=0):
    m = find_member(member_id)
    if not m: return {"error":"Member not found."}
    cur = m["estimated_fico_score"]; sens = 1.0+(cur-600)/400
    impacts = {"miss_payment_30":(-75,"Payment History (35%)"),"miss_payment_60":(-105,"Payment History (35%)"),
               "miss_payment_90":(-130,"Payment History (35%)"),"pay_on_time":(max(5,int(15*(1.5-m["payment_history_ontime_pct"]/100))),"Payment History (35%)"),
               "pay_down_balance":(0,"Utilization (30%)"),"max_out_card":(-35,"Utilization (30%)"),
               "open_new_card":(-8,"New Inquiries (10%)"),"close_oldest_card":(-20,"Credit Age (15%)")}
    if action not in impacts: return {"error":f"Unknown action. Valid: {', '.join(impacts.keys())}"}
    base, factor = impacts[action]
    pts = int(base*sens) if base<0 else base
    exp = f"Action '{action}' on score {cur}."
    if action=="pay_down_balance" and amount>0:
        tl=sum(a.get("credit_limit_or_original",0) for a in m.get("accounts",[]) if a.get("account_type")=="credit_card")
        tb=sum(a.get("current_balance",0) for a in m.get("accounts",[]) if a.get("account_type")=="credit_card")
        if tl>0:
            ou,nu=tb/tl*100,max(0,tb-amount)/tl*100
            def br(u): return 165 if u<=9 else 140 if u<=29 else 100 if u<=49 else 60 if u<=74 else 20
            pts=max(0,br(nu)-br(ou)); exp=f"Paying ${amount:,.0f} moves utilization {ou:.0f}% -> {nu:.0f}%."
    return {"current_score":cur,"projected_score":max(300,min(850,cur+pts)),"point_change":pts,"factor":factor,"explanation":exp}

def simulate_timeline(member_id):
    m = find_member(member_id)
    if not m: return {"error":"Member not found."}
    c=m["estimated_fico_score"]; u=m["credit_utilization_pct"]; iq=m["hard_inquiries_last_12mo"]
    # Handle no-score — show credit building trajectory
    if c == 0 or m["number_of_accounts"] == 0:
        return {"member_name":m["member_name"],"current_score":0,
                "good_path":{"3mo":580,"6mo":640,"12mo":690,
                             "description":"Open secured card + autopay + under 10% utilization + authorized user"},
                "bad_path":{"3mo":0,"6mo":0,"12mo":0,
                            "description":"Do nothing — remain credit invisible with no score"},
                "difference_at_12mo":690}
    g3=c+15+(10 if u>30 else 0); g6=g3+20+(15 if u>30 else 5); g12=g6+25+(10 if iq>0 else 0)
    b3=c-65; b6=b3-30; b12=b6-15
    return {"member_name":m["member_name"],"current_score":c,
            "good_path":{"3mo":min(850,g3),"6mo":min(850,g6),"12mo":min(850,g12),
                         "description":"Pay on time + reduce utilization + no new inquiries"},
            "bad_path":{"3mo":max(300,b3),"6mo":max(300,b6),"12mo":max(300,b12),
                        "description":"Miss payments + max out cards + multiple applications"},
            "difference_at_12mo":min(850,g12)-max(300,b12)}

def generate_action_plan(member_id, target_score=None):
    m = find_member(member_id)
    if not m: return {"error":"Member not found."}
    cur=m["estimated_fico_score"]; target=target_score or max(cur+50, 670); steps=[]
    # Handle no-score / credit invisible
    if cur == 0 or m["number_of_accounts"] == 0:
        return {"member_name":m["member_name"],"current_score":0,"target_score":670,"steps":[
            {"priority":1,"action":"Get a secured credit card (deposit $200-500). Try Discover it Secured or Capital One Platinum Secured.","impact":"Establishes score","why":"You need at least one account to generate a FICO score."},
            {"priority":2,"action":"Set up autopay for the full statement balance immediately","impact":"100% on-time history","why":"Payment history is 35% of your score — one missed payment can drop you 75+ pts."},
            {"priority":3,"action":"Keep utilization under 10% — only charge small purchases ($20-50/month)","impact":"+30-60 pts vs high usage","why":"Utilization is 30% of your score. Low usage = high score."},
            {"priority":4,"action":"Ask a family member to add you as an authorized user on their oldest card","impact":"+50-100 pts potential","why":"Their card's age and history gets added to your report instantly."},
            {"priority":5,"action":"Use pre-qualification tools before ANY application (Capital One, Discover, Credit Karma)","impact":"Avoids hard inquiries","why":"Every rejection adds a hard inquiry that hurts your future score."},
            {"priority":6,"action":"Consider Experian Boost — add rent, utilities, streaming to your report","impact":"+5-15 pts","why":"Free way to add positive data to a thin file."},
            {"priority":7,"action":"Wait 6 months, then apply for a second unsecured card if pre-qualified","impact":"Builds credit mix","why":"Do NOT apply early — too many inquiries on a thin file = rejections."},
        ]}
    tl=m["late_payments_30day"]+m["late_payments_60day"]+m["late_payments_90day"]
    if tl>0 or m["payment_history_ontime_pct"]<98:
        steps.append({"priority":1,"action":"Set up autopay on ALL accounts","impact":"+20-40 pts","why":f"{tl} late payments on record."})
    # Per-card payoff targets
    if m["credit_utilization_pct"]>10:
        cards = [a for a in m.get("accounts",[]) if a["account_type"]=="credit_card" and a["credit_limit_or_original"]>0]
        cards.sort(key=lambda a: a["current_balance"]/a["credit_limit_or_original"], reverse=True)
        target_util = 29 if m["credit_utilization_pct"]>30 else 9
        payoff_details = []
        for card in cards:
            bal = card["current_balance"]
            lim = card["credit_limit_or_original"]
            card_util = bal/lim*100
            card_target = lim * target_util / 100
            if bal > card_target:
                pay_amount = int(bal - card_target)
                payoff_details.append(f"Pay ${pay_amount:,} on {card['account_name']} ({card_util:.0f}% -> {target_util}%)")
        if m["credit_utilization_pct"]>30:
            total_cc_bal = sum(a["current_balance"] for a in cards)
            total_cc_lim = sum(a["credit_limit_or_original"] for a in cards)
            need_to_pay = int(total_cc_bal - total_cc_lim * 0.29)
            detail = f" — pay ${need_to_pay:,} total across cards" if need_to_pay > 0 else ""
            action = f"Pay down cards below 30% (currently {m['credit_utilization_pct']:.0f}%){detail}"
            if payoff_details:
                action += ". Priority: " + payoff_details[0]
            steps.append({"priority":2,"action":action,"impact":"+30-60 pts","why":"Utilization is 30% of score."})
        else:
            action = f"Get utilization from {m['credit_utilization_pct']:.0f}% to under 10%"
            if payoff_details:
                action += ". " + payoff_details[0]
            steps.append({"priority":2,"action":action,"impact":"+10-20 pts","why":"Single-digit util maximizes this factor."})
    if m["credit_utilization_pct"]>20:
        steps.append({"priority":3,"action":"Request credit limit increase (soft pull)","impact":"+5-15 pts","why":"Higher limit = lower utilization."})
    if m["has_collections"]:
        steps.append({"priority":4,"action":"Dispute or negotiate pay-for-delete on collections","impact":"+25-75 pts","why":"Collections severely damage score."})
    if m["avg_account_age_months"]<24:
        steps.append({"priority":5,"action":"Keep all accounts open","impact":"+5-15 pts","why":f"Avg age only {m['avg_account_age_months']}mo."})
    if m["hard_inquiries_last_12mo"]>2:
        steps.append({"priority":6,"action":"Stop applying for new credit","impact":f"+{m['hard_inquiries_last_12mo']*5} pts","why":"Too many inquiries."})
    if m["credit_mix"] in ("credit_card_only","loan_only"):
        steps.append({"priority":7,"action":"Diversify credit mix","impact":"+10-20 pts","why":"Only one type of credit."})
    if not steps:
        steps.append({"priority":1,"action":"Maintain your great habits!","impact":"Steady","why":"Credit is in great shape."})
    return {"member_name":m["member_name"],"current_score":cur,"target_score":target,"steps":steps}

def check_credit_health(member_id):
    m = find_member(member_id)
    if not m: return {"error":"Member not found."}
    s=m["estimated_fico_score"]; strengths=[]; weaknesses=[]
    # Handle no-score / credit invisible
    if s == 0 or m["number_of_accounts"] == 0:
        return {"member_name":m["member_name"],"score":0,"grade":"N/A",
                "strengths":["Clean slate — no negative marks","No debt"],
                "weaknesses":["No credit history at all","Credit invisible — no FICO score yet","Cannot qualify for most credit cards or loans"],
                "top_tip":"Start with a secured credit card ($200-500 deposit) or become an authorized user. Always pre-qualify before applying."}
    if m["payment_history_ontime_pct"]>=98: strengths.append("Excellent payment history")
    else: weaknesses.append(f"Payment history at {m['payment_history_ontime_pct']}%")
    if m["credit_utilization_pct"]<=30: strengths.append(f"Good utilization ({m['credit_utilization_pct']:.0f}%)")
    else: weaknesses.append(f"High utilization ({m['credit_utilization_pct']:.0f}%)")
    if m["avg_account_age_months"]>=48: strengths.append(f"Strong history ({m['avg_account_age_months']//12}yr)")
    elif m["avg_account_age_months"]<12: weaknesses.append("Very short credit history")
    if m["has_collections"]: weaknesses.append("Collection on file")
    if m["hard_inquiries_last_12mo"]>3: weaknesses.append(f"Too many inquiries ({m['hard_inquiries_last_12mo']})")
    grade="A" if s>=740 else "B" if s>=670 else "C" if s>=580 else "D" if s>=500 else "F"
    return {"member_name":m["member_name"],"score":s,"grade":grade,
            "strengths":strengths or ["Building!"],"weaknesses":weaknesses or ["No major issues!"],
            "top_tip":weaknesses[0] if weaknesses else "Keep it up!"}

TOOL_DEFINITIONS = [
    {"type":"function","function":{"name":"get_member_profile","description":"Get member's full credit profile including score, all accounts with per-card utilization, payment history, debt-to-income ratio, and key observations. Always call this first to understand the member.","parameters":{"type":"object","properties":{"member_id":{"type":"string","description":"Member ID (M0001-M0200) or name"}},"required":["member_id"]}}},
    {"type":"function","function":{"name":"simulate_payment_impact","description":"Simulate how a financial action affects credit score. Actions: miss_payment_30, miss_payment_60, miss_payment_90, pay_on_time, pay_down_balance, max_out_card, open_new_card, close_oldest_card","parameters":{"type":"object","properties":{"member_id":{"type":"string","description":"Member ID"},"action":{"type":"string","description":"Action to simulate"},"amount":{"type":"number","description":"Dollar amount for pay_down_balance"}},"required":["member_id","action"]}}},
    {"type":"function","function":{"name":"simulate_timeline","description":"Project score over 3/6/12 months comparing good vs bad behavior paths.","parameters":{"type":"object","properties":{"member_id":{"type":"string","description":"Member ID"}},"required":["member_id"]}}},
    {"type":"function","function":{"name":"generate_action_plan","description":"Generate prioritized step-by-step credit improvement plan.","parameters":{"type":"object","properties":{"member_id":{"type":"string","description":"Member ID"},"target_score":{"type":"integer","description":"Target score (optional)"}},"required":["member_id"]}}},
    {"type":"function","function":{"name":"check_credit_health","description":"Credit health checkup with grade, strengths, weaknesses.","parameters":{"type":"object","properties":{"member_id":{"type":"string","description":"Member ID"}},"required":["member_id"]}}},
    {"type":"function","function":{"name":"get_transaction_history","description":"Get 6-month transaction and payment history for all accounts. Shows spending, payments, and on-time/late status per month. Use for detailed analysis.","parameters":{"type":"object","properties":{"member_id":{"type":"string","description":"Member ID"}},"required":["member_id"]}}},
]

TOOL_FUNCTIONS = {
    "get_member_profile": lambda a: get_member_profile(a["member_id"]),
    "simulate_payment_impact": lambda a: simulate_payment_impact(a["member_id"],a["action"],a.get("amount",0)),
    "simulate_timeline": lambda a: simulate_timeline(a["member_id"]),
    "generate_action_plan": lambda a: generate_action_plan(a["member_id"],a.get("target_score")),
    "check_credit_health": lambda a: check_credit_health(a["member_id"]),
    "get_transaction_history": lambda a: get_transaction_history(a["member_id"]),
}
