from .text import norm_text


def current_role(candidate):
    for role in candidate.get("career_history", []):
        if role.get("is_current"):
            return role
    career_history = candidate.get("career_history", [])
    return career_history[0] if career_history else {}


def role_text(role):
    return norm_text(
        " ".join(
            [
                role.get("title", ""),
                role.get("industry", ""),
                role.get("description", ""),
            ]
        )
    )


def candidate_text(candidate):
    profile = candidate.get("profile", {})
    career_history = candidate.get("career_history", [])
    skills = candidate.get("skills", [])

    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
    ]
    for role in career_history:
        parts.extend(
            [
                role.get("title", ""),
                role.get("industry", ""),
                role.get("description", ""),
            ]
        )
    parts.extend(skill.get("name", "") for skill in skills)
    return norm_text(" ".join(parts))


def current_candidate_text(candidate):
    profile = candidate.get("profile", {})
    role = current_role(candidate)
    skills = candidate.get("skills", [])
    return norm_text(
        " ".join(
            [
                profile.get("headline", ""),
                profile.get("summary", ""),
                profile.get("current_title", ""),
                profile.get("current_industry", ""),
                role_text(role),
                " ".join(skill.get("name", "") for skill in skills),
            ]
        )
    )


def career_companies(candidate):
    return [norm_text(role.get("company")) for role in candidate.get("career_history", [])]


def role_duration(role):
    try:
        return int(role.get("duration_months") or 0)
    except (TypeError, ValueError):
        return 0
