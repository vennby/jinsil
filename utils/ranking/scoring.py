import math

from .config import (
    ADJACENT_ENGINEERING_TITLE_TERMS,
    ADJACENT_TERMS,
    CONSULTING_COMPANIES,
    CORE_RETRIEVAL_TERMS,
    EVALUATION_TERMS,
    FINAL_SCORE_SCALE,
    HANDS_ON_TITLE_TERMS,
    LEADERSHIP_TERMS,
    MUST_HAVE_TERMS,
    NEGATIVE_TERMS,
    NON_TARGET_AI_SIGNALS,
    PRODUCT_OWNERSHIP_TERMS,
    PRODUCT_SIGNALS,
    PRODUCTION_TERMS,
    PROFICIENCY_WEIGHT,
    PURE_RESEARCH_SIGNALS,
    REFERENCE_DATE,
)
from .features import (
    candidate_text,
    career_companies,
    current_candidate_text,
    role_duration,
)
from .text import clamp, contains_any, count_weighted_terms, norm_text, phrase_present


def parse_date(value):
    if not value:
        return None
    try:
        from datetime import date

        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def skill_score(candidate):
    skills = candidate.get("skills", [])
    assessments = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})

    total = 0.0
    hit_names = []
    for skill in skills:
        name = norm_text(skill.get("name"))
        if not name or contains_any(name, NON_TARGET_AI_SIGNALS):
            continue

        relevance = 0.0
        for term, weight in MUST_HAVE_TERMS.items():
            if phrase_present(name, term):
                relevance = max(relevance, weight)
        for term, weight in ADJACENT_TERMS.items():
            if phrase_present(name, term):
                relevance = max(relevance, weight * 0.65)

        if relevance == 0:
            continue

        proficiency = PROFICIENCY_WEIGHT.get(norm_text(skill.get("proficiency")), 0.45)
        duration = min(float(skill.get("duration_months") or 0) / 36.0, 1.0)
        endorsements = min(float(skill.get("endorsements") or 0) / 20.0, 1.0)
        assessment = float(assessments.get(skill.get("name"), 0) or 0) / 100.0
        trust = 0.55 * proficiency + 0.2 * duration + 0.15 * endorsements + 0.1 * assessment

        total += relevance * trust
        hit_names.append(skill.get("name", ""))

    return clamp(total / 5.0), hit_names[:5]


def technical_relevance(candidate, text):
    must_score, must_hits = count_weighted_terms(text, MUST_HAVE_TERMS)
    adjacent_score, adjacent_hits = count_weighted_terms(text, ADJACENT_TERMS)
    skills, skill_hits = skill_score(candidate)

    core_signal_count = sum(1 for term in CORE_RETRIEVAL_TERMS if phrase_present(text, term))
    eval_signal_count = sum(1 for term in EVALUATION_TERMS if phrase_present(text, term))
    production_signal_count = sum(1 for term in PRODUCTION_TERMS if phrase_present(text, term))

    text_score = clamp((must_score + 0.45 * adjacent_score) / 9.0)
    score = clamp(0.55 * text_score + 0.45 * skills)

    if core_signal_count == 0:
        score = min(score, 0.38)
    elif core_signal_count == 1 and eval_signal_count == 0:
        score = min(score, 0.68)

    hits = sorted(set(must_hits[:5] + adjacent_hits[:3] + [s.lower() for s in skill_hits[:3]]))
    details = {
        "core_signal_count": core_signal_count,
        "eval_signal_count": eval_signal_count,
        "production_signal_count": production_signal_count,
    }
    return score, hits, details


def seniority_fit(candidate):
    years = float(candidate.get("profile", {}).get("years_of_experience") or 0)
    if 5 <= years <= 9:
        return 1.0
    if 4 <= years < 5:
        return 0.82
    if 9 < years <= 12:
        return 0.78
    if 3 <= years < 4:
        return 0.45
    if 12 < years <= 15:
        return 0.45
    return 0.18


def title_fit(candidate):
    current_title = norm_text(candidate.get("profile", {}).get("current_title"))
    if contains_any(current_title, HANDS_ON_TITLE_TERMS):
        if contains_any(
            current_title,
            ("recommendation", "search", "ml", "ai", "data scientist", "machine learning"),
        ):
            return 1.0
        return 0.78
    if contains_any(current_title, ADJACENT_ENGINEERING_TITLE_TERMS):
        return 0.42
    if contains_any(current_title, NEGATIVE_TERMS):
        return 0.05
    return 0.25


def career_evidence(candidate, text):
    profile = candidate.get("profile", {})
    current_title = norm_text(profile.get("current_title"))
    current_text = current_candidate_text(candidate)
    career_history = candidate.get("career_history", [])

    hands_on_title = contains_any(current_title, HANDS_ON_TITLE_TERMS)
    current_core = contains_any(current_text, CORE_RETRIEVAL_TERMS)
    historical_core = contains_any(text, CORE_RETRIEVAL_TERMS)
    production = contains_any(text, PRODUCTION_TERMS)
    evaluation = contains_any(text, EVALUATION_TERMS)
    product = contains_any(text, PRODUCT_SIGNALS | PRODUCT_OWNERSHIP_TERMS)
    leadership = contains_any(text, LEADERSHIP_TERMS)
    long_tenures = sum(1 for role in career_history if role_duration(role) >= 24)
    trajectory = min(long_tenures / 2.0, 1.0)

    return clamp(
        0.18 * hands_on_title
        + 0.2 * current_core
        + 0.12 * historical_core
        + 0.17 * production
        + 0.14 * evaluation
        + 0.1 * product
        + 0.04 * leadership
        + 0.05 * trajectory
    )


def evidence_depth(candidate, text, technical_details):
    """Reward JD-shaped evidence combinations, not isolated term hits."""
    current_text = current_candidate_text(candidate)
    core_current = contains_any(current_text, CORE_RETRIEVAL_TERMS)
    core_any = technical_details["core_signal_count"] >= 2
    eval_any = technical_details["eval_signal_count"] > 0
    production_any = technical_details["production_signal_count"] > 0
    product_any = contains_any(text, PRODUCT_OWNERSHIP_TERMS | PRODUCT_SIGNALS)
    leadership_any = contains_any(text, LEADERSHIP_TERMS)

    return clamp(
        0.28 * core_current
        + 0.22 * core_any
        + 0.18 * eval_any
        + 0.18 * production_any
        + 0.1 * product_any
        + 0.04 * leadership_any
    )


def product_company_fit(candidate, text):
    companies = career_companies(candidate)
    consulting_roles = sum(
        any(company == service or service in company for service in CONSULTING_COMPANIES)
        for company in companies
    )
    consulting_share = consulting_roles / max(len(companies), 1)

    product_signal = clamp(
        sum(1 for term in PRODUCT_SIGNALS | PRODUCT_OWNERSHIP_TERMS if phrase_present(text, term))
        / 5.0
    )
    service_penalty = 0.55 * consulting_share
    return clamp(product_signal - service_penalty + 0.35)


def location_fit(candidate):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    location = norm_text(profile.get("location"))
    country = norm_text(profile.get("country"))

    if country and "india" not in country:
        return 0.25 if signals.get("willing_to_relocate") else 0.08

    preferred_cities = ("pune", "noida", "delhi", "gurgaon", "gurugram", "mumbai", "hyderabad")
    if any(city in location for city in preferred_cities):
        return 1.0
    return 0.72 if signals.get("willing_to_relocate") else 0.52


def engagement_availability(candidate):
    signals = candidate.get("redrob_signals", {})
    last_active = parse_date(signals.get("last_active_date"))
    if last_active:
        days_inactive = max((REFERENCE_DATE - last_active).days, 0)
        recency = math.exp(-days_inactive / 180.0)
    else:
        recency = 0.35

    response_rate = float(signals.get("recruiter_response_rate") or 0)
    response_time = float(signals.get("avg_response_time_hours") or 999)
    response_speed = clamp(1.0 - response_time / 168.0)
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.35
    notice = int(signals.get("notice_period_days") or 180)
    notice_score = 1.0 if notice <= 30 else 0.72 if notice <= 60 else 0.42 if notice <= 90 else 0.18

    return clamp(
        0.28 * recency
        + 0.25 * response_rate
        + 0.12 * response_speed
        + 0.18 * open_to_work
        + 0.17 * notice_score
    )


def trust_quality(candidate):
    signals = candidate.get("redrob_signals", {})
    completeness = float(signals.get("profile_completeness_score") or 0) / 100.0
    email = 1.0 if signals.get("verified_email") else 0.0
    phone = 1.0 if signals.get("verified_phone") else 0.0
    linkedin = 1.0 if signals.get("linkedin_connected") else 0.0
    interview = float(signals.get("interview_completion_rate") or 0)
    offer = float(signals.get("offer_acceptance_rate") or -1)
    offer_score = 0.5 if offer < 0 else offer

    return clamp(
        0.28 * completeness
        + 0.12 * email
        + 0.12 * phone
        + 0.1 * linkedin
        + 0.25 * interview
        + 0.13 * offer_score
    )


def market_signal(candidate):
    signals = candidate.get("redrob_signals", {})
    views = min(float(signals.get("profile_views_received_30d") or 0) / 60.0, 1.0)
    saves = min(float(signals.get("saved_by_recruiters_30d") or 0) / 20.0, 1.0)
    search = min(float(signals.get("search_appearance_30d") or 0) / 150.0, 1.0)
    github = float(signals.get("github_activity_score") or -1)
    github_score = 0.35 if github < 0 else github / 100.0
    return clamp(0.2 * views + 0.2 * saves + 0.2 * search + 0.4 * github_score)


def penalty_score(candidate, text):
    profile = candidate.get("profile", {})
    current_title = norm_text(profile.get("current_title"))
    career_history = candidate.get("career_history", [])
    skills = candidate.get("skills", [])

    penalty = 0.0
    reasons = []

    if contains_any(current_title, NEGATIVE_TERMS):
        penalty += 0.32
        reasons.append("current role is outside hands-on AI engineering")

    if not contains_any(current_title, HANDS_ON_TITLE_TERMS | ADJACENT_ENGINEERING_TITLE_TERMS):
        penalty += 0.12
        if not reasons:
            reasons.append("current title is not a target AI/backend/search engineering title")

    companies = [norm_text(role.get("company")) for role in career_history]
    if companies and all(
        any(service == company or service in company for service in CONSULTING_COMPANIES)
        for company in companies
    ):
        penalty += 0.16
        reasons.append("consulting-only career pattern")

    if contains_any(text, PURE_RESEARCH_SIGNALS) and not phrase_present(text, "production"):
        penalty += 0.14
        reasons.append("research signal without production evidence")

    if contains_any(text, NON_TARGET_AI_SIGNALS) and not contains_any(
        text, ("nlp", "retrieval", "ranking", "search")
    ):
        penalty += 0.12
        reasons.append("AI background appears outside NLP/retrieval")

    expert_zero_duration = sum(
        1
        for skill in skills
        if norm_text(skill.get("proficiency")) == "expert"
        and int(skill.get("duration_months") or 0) == 0
    )
    if expert_zero_duration >= 3:
        penalty += 0.18
        reasons.append("honeypot-like expert skills with no duration")

    ai_skill_count = sum(
        1
        for skill in skills
        if any(phrase_present(norm_text(skill.get("name")), term) for term in MUST_HAVE_TERMS)
    )
    if ai_skill_count >= 7 and not contains_any(
        text, ("deployed", "production", "shipped", "built")
    ):
        penalty += 0.13
        reasons.append("AI keyword density without delivery evidence")

    return clamp(penalty, 0.0, 0.55), reasons


def score_candidate(candidate):
    text = candidate_text(candidate)
    technical, hits, technical_details = technical_relevance(candidate, text)
    title = title_fit(candidate)
    career = career_evidence(candidate, text)
    depth = evidence_depth(candidate, text, technical_details)
    seniority = seniority_fit(candidate)
    product = product_company_fit(candidate, text)
    location = location_fit(candidate)
    engagement = engagement_availability(candidate)
    trust = trust_quality(candidate)
    market = market_signal(candidate)
    penalty, penalty_reasons = penalty_score(candidate, text)

    base = (
        0.25 * technical
        + 0.16 * career
        + 0.14 * depth
        + 0.11 * title
        + 0.11 * seniority
        + 0.08 * product
        + 0.06 * location
        + 0.07 * engagement
        + 0.02 * trust
    )
    hireability_multiplier = clamp(0.82 + 0.2 * engagement + 0.08 * trust, 0.78, 1.08)
    raw_score = max(base - penalty, 0.0) * hireability_multiplier
    score = clamp(raw_score / FINAL_SCORE_SCALE)

    if technical_details["core_signal_count"] == 0:
        score = min(score, 0.42)
    if depth < 0.35:
        score = min(score, 0.62)
    if title < 0.3 and technical_details["core_signal_count"] < 2:
        score = min(score, 0.32)
    if title < 0.1:
        score = min(score, 0.24)

    components = {
        "technical": technical,
        "title": title,
        "career": career,
        "evidence_depth": depth,
        "seniority": seniority,
        "product": product,
        "location": location,
        "engagement": engagement,
        "trust": trust,
        "market": market,
        "penalty": penalty,
        "hireability_multiplier": hireability_multiplier,
        "raw_score": raw_score,
        "hits": hits,
        "technical_details": technical_details,
        "penalty_reasons": penalty_reasons,
    }
    return score, components
