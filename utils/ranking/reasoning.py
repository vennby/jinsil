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


def profile_terms(jd_profile, section, key, fallback):
    if not jd_profile:
        return fallback
    values = jd_profile.get(section, {})
    return values[key] if key in values else fallback


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _percent(value):
    return f"{100 * value:.0f}%"


def _compact_join(items, fallback="not explicit"):
    items = [str(item) for item in items if item]
    return ", ".join(items) if items else fallback


def _signal_count(count, label):
    suffix = "" if count == 1 else "s"
    return f"{count} {label} signal{suffix}"


def top_relevant_skills(candidate, jd_profile=None, limit=4):
    must_terms = profile_terms(jd_profile, "must_have_evidence", "technical_terms", MUST_HAVE_TERMS)
    adjacent_terms = profile_terms(
        jd_profile,
        "strong_positive_evidence",
        "adjacent_terms",
        ADJACENT_TERMS,
    )
    non_target_ai = profile_terms(
        jd_profile,
        "negative_evidence",
        "non_target_ai_domains",
        NON_TARGET_AI_SIGNALS,
    )
    ranked = []
    for skill in candidate.get("skills", []):
        name = skill.get("name", "")
        normalized = norm_text(name)
        if not normalized or contains_any(normalized, non_target_ai):
            continue

        relevance = 0.0
        for term, weight in must_terms.items():
            if phrase_present(normalized, term):
                relevance = max(relevance, weight)
        for term, weight in adjacent_terms.items():
            if phrase_present(normalized, term):
                relevance = max(relevance, weight * 0.6)

        if relevance:
            proficiency = PROFICIENCY_WEIGHT.get(norm_text(skill.get("proficiency")), 0.45)
            duration = min(float(skill.get("duration_months") or 0) / 36.0, 1.0)
            ranked.append(
                (
                    relevance * (0.75 * proficiency + 0.25 * duration),
                    {
                        "name": name,
                        "proficiency": skill.get("proficiency", "unknown"),
                        "duration_months": _safe_int(skill.get("duration_months")),
                        "endorsements": _safe_int(skill.get("endorsements")),
                    },
                )
            )

    ranked.sort(reverse=True, key=lambda row: row[0])
    return [skill for _score, skill in ranked[:limit]]


def strongest_career_evidence(candidate, jd_profile=None, limit=2):
    ranked = []
    evidence_terms = (
        set(profile_terms(jd_profile, "must_have_evidence", "retrieval_ranking_terms", CORE_RETRIEVAL_TERMS))
        | set(profile_terms(jd_profile, "must_have_evidence", "evaluation_terms", EVALUATION_TERMS))
        | set(profile_terms(jd_profile, "must_have_evidence", "production_terms", PRODUCTION_TERMS))
    )
    for role in candidate.get("career_history", []):
        text = role_text(role)
        hits = [term for term in evidence_terms if phrase_present(text, term)]

        score = len(set(hits))
        if role.get("is_current"):
            score += 1.5
        score += min(int(role.get("duration_months") or 0) / 36.0, 1.0)

        if score > 0:
            ranked.append((score, role, sorted(set(hits))[:5]))

    ranked.sort(reverse=True, key=lambda row: row[0])
    return [(role, hits) for _score, role, hits in ranked[:limit]]


def concern_list(candidate, components, limit=3):
    signals = candidate.get("redrob_signals", {})
    concerns = list(components["penalty_reasons"])

    if components["penalty_reasons"]:
        concerns.extend(components["penalty_reasons"])

    notice = _safe_int(signals.get("notice_period_days"))
    if notice > 90:
        concerns.append(f"notice period is high at {notice} days")
    elif notice > 60:
        concerns.append(f"notice period is {notice} days")
    if components["engagement"] < 0.35:
        response_rate = _safe_float(signals.get("recruiter_response_rate"))
        concerns.append(f"engagement is weak with response rate {response_rate:.2f}")
    if components["technical_details"]["eval_signal_count"] == 0:
        concerns.append("ranking/evaluation evidence is not explicit")
    if components["evidence_depth"] < 0.45:
        concerns.append("evidence is more adjacent than directly JD-shaped")

    unique = []
    for concern in concerns:
        if concern and concern not in unique:
            unique.append(concern)
    return unique[:limit]


def skill_phrase(skills):
    phrases = []
    for skill in skills:
        details = []
        proficiency = skill.get("proficiency")
        duration = skill.get("duration_months")
        endorsements = skill.get("endorsements")
        if proficiency:
            details.append(str(proficiency))
        if duration:
            details.append(f"{duration} months")
        if endorsements:
            details.append(f"{endorsements} endorsements")

        suffix = f" ({', '.join(details)})" if details else ""
        phrases.append(f"{skill['name']}{suffix}")
    return _compact_join(phrases, fallback="no strongly matched declared skill")


def career_phrase(career_evidence):
    phrases = []
    for role, hits in career_evidence:
        title = role.get("title", "role")
        company = role.get("company", "company")
        duration = _safe_int(role.get("duration_months"))
        current = "current " if role.get("is_current") else ""
        hit_text = _compact_join(hits[:4])
        duration_text = f" for {duration} months" if duration else ""
        phrases.append(f"{current}{title} at {company}{duration_text} shows {hit_text}")
    return _compact_join(phrases, fallback="career evidence is limited")


def coverage_phrase(components):
    details = components["technical_details"]
    coverage = [
        _signal_count(details["core_signal_count"], "retrieval/ranking"),
        _signal_count(details["eval_signal_count"], "evaluation"),
        _signal_count(details["production_signal_count"], "production"),
    ]
    if components["semantic_score"]:
        coverage.append(f"semantic score {_percent(components['semantic_score'])}")
    if components["coverage_score"]:
        coverage.append(f"JD coverage score {_percent(components['coverage_score'])}")
    return ", ".join(coverage)


def seniority_phrase(years, components, jd_profile):
    ideal = jd_profile.get("ideal_profile", {}) if jd_profile else {}
    exp_min = _safe_float(ideal.get("experience_min"), 5.0)
    exp_max = _safe_float(ideal.get("experience_max"), 9.0)
    if exp_max >= 99:
        return f"{years} years where the JD does not state a strict experience band"
    band = f"{exp_min:g}-{exp_max:g}"
    if components["seniority"] >= 0.75:
        return f"{years} years in or near the JD's {band} year seniority band"
    return f"{years} years outside the ideal {band} year band"


def make_reasoning(candidate, components, jd_profile=None):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    years = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "candidate")
    location = profile.get("location", "unknown location")
    current_company = profile.get("current_company", "current company")
    country = profile.get("country", "")
    notice = _safe_int(signals.get("notice_period_days"))
    response_rate = _safe_float(signals.get("recruiter_response_rate"))
    response_time = _safe_float(signals.get("avg_response_time_hours"), default=999.0)
    completeness = _safe_float(signals.get("profile_completeness_score")) / 100.0

    skills = top_relevant_skills(candidate, jd_profile)
    career_evidence = strongest_career_evidence(candidate, jd_profile)
    concerns = concern_list(candidate, components)

    seniority_text = seniority_phrase(years, components, jd_profile)
    logistics = (
        f"{location}{', ' + country if country else ''}; notice {notice} days; "
        f"response rate {response_rate:.2f}; average response time {response_time:.0f}h"
    )
    trust_bits = [
        f"profile completeness {_percent(completeness)}",
        "verified email" if signals.get("verified_email") else "",
        "verified phone" if signals.get("verified_phone") else "",
        "LinkedIn connected" if signals.get("linkedin_connected") else "",
        "open to work" if signals.get("open_to_work_flag") else "",
    ]
    risk_text = _compact_join(concerns, fallback="no major penalty signal surfaced")

    score_summary = (
        f"technical {_percent(components['technical'])}, "
        f"career {_percent(components['career'])}, "
        f"depth {_percent(components['evidence_depth'])}, "
        f"title {_percent(components['title'])}, "
        f"seniority {_percent(components['seniority'])}"
    )
    if components["hybrid_score"]:
        score_summary += f", hybrid precompute {_percent(components['hybrid_score'])}"

    return (
        f"Fit summary: {title} at {current_company} is a strong JD match with "
        f"{seniority_text}; component evidence is {score_summary}; JD evidence is "
        f"{career_phrase(career_evidence)} with coverage of {coverage_phrase(components)}; "
        f"skill proof is {skill_phrase(skills[:4])}; hireability and trust are "
        f"{logistics}, {_compact_join(trust_bits)}; "
        f"risk check is {risk_text}."
    )
