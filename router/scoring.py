from .models import Decision, Lead, Signals


def score_and_route(lead: Lead, signals: Signals) -> Decision:
    account_score, persona_score, reasons = 0, 0, []
    if lead.employee_count >= 1000:
        account_score += 20; reasons.append("Account: 1,000+ employees (+20)")
    elif lead.employee_count >= 200:
        account_score += 12; reasons.append("Account: 200–999 employees (+12)")
    if signals.b2b:
        account_score += 20; reasons.append("Account: B2B/platform language found (+20)")
    if signals.enterprise:
        account_score += 15; reasons.append("Account: enterprise language found (+15)")
    if signals.ai_related:
        account_score += 8; reasons.append("Account: AI signal found (+8)")
    if signals.sales_motion == "enterprise":
        account_score += 7; reasons.append("Account: enterprise sales motion (+7)")

    title = lead.title.lower()
    if any(term in title for term in ("revenue operations", "sales operations", "go to market operations", "revenue systems", "business systems")):
        persona_score += 18; reasons.append("Persona: GTM operations owner (+18)")
    elif any(term in title for term in ("sales strategy", "revenue strategy", "commercial operations", "sales enablement", "revenue enablement")):
        persona_score += 15; reasons.append("Persona: revenue strategy/enabling function (+15)")
    elif any(term in title for term in ("customer success", "customer operations", "customer experience", "partner", "partnership")):
        persona_score += 12; reasons.append("Persona: customer or partner function (+12)")
    elif "support" in title:
        persona_score += 7; reasons.append("Persona: support function (+7)")

    if "vp" in title or "head" in title:
        persona_score += 12; reasons.append("Persona: executive sponsor seniority (+12)")
    elif "director" in title:
        persona_score += 9; reasons.append("Persona: director seniority (+9)")
    elif "manager" in title:
        persona_score += 5; reasons.append("Persona: manager seniority (+5)")

    account_score, persona_score = min(account_score, 70), min(persona_score, 30)
    score = account_score + persona_score
    if not signals.scraped or signals.confidence < 0.5:
        route = "Human Review"
        reasons.append("insufficient website evidence; verify manually")
    elif score >= 80:
        route = "Tier 1"
    elif score >= 50:
        route = "Nurture"
    else:
        route = "Disqualify"
    angle = (f"Explore how {lead.company}'s {lead.industry.lower()} teams could improve "
             f"customer and revenue operations; tailor after human validation.")
    return Decision(score=score, account_score=account_score, persona_score=persona_score,
                    route=route, reasons=reasons, outreach_angle=angle)
