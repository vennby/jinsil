from .config import (
    ADJACENT_TERMS,
    CORE_RETRIEVAL_TERMS,
    EVALUATION_TERMS,
    MUST_HAVE_TERMS,
    NON_TARGET_AI_SIGNALS,
    PRODUCTION_TERMS,
    PROFICIENCY_WEIGHT,
)
from .features import role_text
from .text import contains_any, norm_text, phrase_present


def top_relevant_skills(candidate, limit=4):
    ranked = []
    for skill in candidate.get("skills", []):
        name = skill.get("name", "")
        normalized = norm_text(name)
        if not normalized or contains_any(normalized, NON_TARGET_AI_SIGNALS):
            continue

        relevance = 0.0
        for term, weight in MUST_HAVE_TERMS.items():
            if phrase_present(normalized, term):
                relevance = max(relevance, weight)
        for term, weight in ADJACENT_TERMS.items():
            if phrase_present(normalized, term):
                relevance = max(relevance, weight * 0.6)

        if relevance:
            proficiency = PROFICIENCY_WEIGHT.get(norm_text(skill.get("proficiency")), 0.45)
            duration = min(float(skill.get("duration_months") or 0) / 36.0, 1.0)
            ranked.append((relevance * (0.75 * proficiency + 0.25 * duration), name))

    ranked.sort(reverse=True)
    return [name for _score, name in ranked[:limit]]


def best_career_evidence(candidate):
    best = (0.0, None, [])
    evidence_terms = CORE_RETRIEVAL_TERMS | EVALUATION_TERMS | PRODUCTION_TERMS
    for role in candidate.get("career_history", []):
        text = role_text(role)
        hits = [term for term in evidence_terms if phrase_present(text, term)]

        score = len(set(hits))
        if role.get("is_current"):
            score += 1.5
        score += min(int(role.get("duration_months") or 0) / 36.0, 1.0)

        if score > best[0]:
            best = (score, role, sorted(set(hits))[:4])

    return best[1], best[2]


def strongest_concern(candidate, components):
    signals = candidate.get("redrob_signals", {})
    if components["penalty_reasons"]:
        return components["penalty_reasons"][0]

    notice = int(signals.get("notice_period_days") or 0)
    if notice > 90:
        return f"notice period is high at {notice} days"
    if notice > 60:
        return f"notice period is {notice} days"
    if components["engagement"] < 0.35:
        response_rate = float(signals.get("recruiter_response_rate") or 0)
        return f"engagement is weak with response rate {response_rate:.2f}"
    if components["technical_details"]["eval_signal_count"] == 0:
        return "ranking/evaluation evidence is not explicit"
    if components["evidence_depth"] < 0.45:
        return "evidence is more adjacent than directly JD-shaped"
    return ""


def make_reasoning(candidate, components):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    years = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "candidate")
    location = profile.get("location", "unknown location")
    current_company = profile.get("current_company", "current company")
    notice = signals.get("notice_period_days", "?")
    response_rate = float(signals.get("recruiter_response_rate") or 0)

    skills = top_relevant_skills(candidate)
    role, role_hits = best_career_evidence(candidate)
    concern = strongest_concern(candidate, components)

    evidence_parts = []
    if role and role_hits:
        role_title = role.get("title", "prior role")
        duration = role.get("duration_months", 0)
        evidence_parts.append(
            f"{role_title} work mentions {', '.join(role_hits[:3])} over {duration} months"
        )
    elif components["hits"]:
        evidence_parts.append(f"profile mentions {', '.join(components['hits'][:3])}")

    if skills:
        evidence_parts.append("relevant skills: " + ", ".join(skills[:3]))

    if components["seniority"] >= 0.75:
        evidence_parts.append(f"{years} years is close to the JD's seniority band")
    else:
        evidence_parts.append(f"{years} years is outside the ideal 5-9 year band")

    if components["engagement"] >= 0.55:
        evidence_parts.append(f"response rate {response_rate:.2f} and notice {notice} days")
    else:
        evidence_parts.append(
            f"availability is weaker: response {response_rate:.2f}, notice {notice} days"
        )

    first_fact = evidence_parts[0] if evidence_parts else "available evidence is limited"
    second_fact = evidence_parts[1] if len(evidence_parts) > 1 else first_fact
    third_fact = (
        evidence_parts[2]
        if len(evidence_parts) > 2
        else "overall fit is driven by the available technical and career evidence"
    )

    first_sentence = (
        f"{title} at {current_company} in {location}; {first_fact} and {second_fact}."
    )
    if concern:
        return f"{first_sentence} {third_fact}; concern: {concern}."
    return f"{first_sentence} {third_fact}."
