#!/usr/bin/env python3
import csv
import gzip
import io
import json
import os
import tempfile
from pathlib import Path

import streamlit as st

from utils.ranking.precompute import compute_precompute_artifact
from utils.ranking.jd_understanding import build_jd_understanding, jd_retrieval_terms
from utils.ranking.ranker import rank_candidates


SAMPLE_CANDIDATES = "sample_candidates.json"
DEFAULT_JD_PATH = Path("instructions/JD.md")
PARTICIPANT_NOTE_HEADING = "## Final note for the participants of the Redrob hackathon"
SUPPORTED_EXTENSIONS = {"json", "jsonl", "gz"}
PREVIEW_COLUMN_OPTIONS = {
    "Candidate ID": "candidate_id",
    "Current title": "current_title",
    "Headline": "headline",
    "Location": "location",
    "Country": "country",
    "Years experience": "years_experience",
    "Current company": "current_company",
    "Current industry": "current_industry",
    "Top skills": "top_skills",
    "Skill count": "skill_count",
    "Current role title": "current_role_title",
    "Current role company": "current_role_company",
    "Current role duration": "current_role_duration",
    "Notice period": "notice_period",
    "Response rate": "response_rate",
    "Open to work": "open_to_work",
    "Profile completeness": "profile_completeness",
    "Verified email": "verified_email",
}
DEFAULT_PREVIEW_COLUMNS = [
    "Candidate ID",
    "Current title",
    "Location",
    "Years experience",
    "Top skills",
]


st.set_page_config(
    page_title="jinsil",
    page_icon="search",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
      :root {
        --ink: #0f172a;
        --muted: #64748b;
        --line: #e2e8f0;
        --blue: #2563eb;
        --blue-dark: #1d4ed8;
        --soft: #f8fafc;
        --soft-blue: #eff6ff;
        --soft-orange: #fff7ed;
      }

      .block-container {
        max-width: none;
        padding: .6rem .7rem .75rem .7rem;
      }

      [data-testid="stHeader"] {
        display: none;
      }

      [data-testid="stToolbar"] {
        display: none;
      }

      .landing-brand {
        display: inline-flex;
        align-items: center;
        margin-bottom: 1rem;
        color: var(--ink);
        font-size: 1.15rem;
        font-weight: 950;
        letter-spacing: -.04em;
      }

      .landing-brand span {
        color: var(--blue);
      }

      .landing-hero {
        position: relative;
        box-sizing: border-box;
        overflow: hidden;
        height: calc(100vh - 1.35rem);
        min-height: 520px;
        padding: clamp(2rem, 4.2vw, 4.2rem);
        border-radius: 1.8rem;
        border: 1px solid #bfdbfe;
        background:
          radial-gradient(circle at 88% 12%, rgba(251, 146, 60, .24), transparent 32%),
          radial-gradient(circle at 8% 10%, rgba(37, 99, 235, .18), transparent 28%),
          linear-gradient(135deg, #ffffff 0%, #eff6ff 52%, #fff7ed 100%);
        box-shadow: 0 28px 70px rgba(37, 99, 235, .09);
        display: grid;
        grid-template-columns: minmax(0, 1.32fr) minmax(310px, .68fr);
        align-items: center;
        gap: clamp(1.25rem, 3vw, 3.2rem);
      }

      .landing-hero-copy {
        min-width: 0;
      }

      .landing-eyebrow {
        display: inline-flex;
        padding: .42rem .78rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, .1);
        color: var(--blue-dark);
        font-size: .8rem;
        font-weight: 850;
        letter-spacing: .06em;
        text-transform: uppercase;
      }

      .landing-hero h1 {
        max-width: 930px;
        margin: 1rem 0 .8rem 0;
        color: var(--ink);
        font-size: clamp(2.45rem, 5.2vw, 5rem);
        line-height: .98;
        letter-spacing: -.065em;
      }

      .landing-hero p {
        max-width: 820px;
        margin: 0;
        color: #475569;
        font-size: clamp(1.05rem, 1.5vw, 1.22rem);
        line-height: 1.7;
      }

      .landing-pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: .6rem;
        margin-top: 1.35rem;
      }

      .landing-pill {
        padding: .55rem .8rem;
        border-radius: 999px;
        border: 1px solid #dbeafe;
        background: rgba(255,255,255,.72);
        color: #334155;
        font-size: .9rem;
        font-weight: 700;
      }

      .landing-cta-panel {
        position: relative;
        border: 1px solid rgba(191, 219, 254, .95);
        border-radius: 1.55rem;
        padding: 1.45rem;
        background:
          linear-gradient(180deg, rgba(255,255,255,.9) 0%, rgba(248,250,252,.72) 100%);
        box-shadow: 0 22px 55px rgba(15, 23, 42, .11);
        backdrop-filter: blur(16px);
      }

      .landing-cta-panel::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: inherit;
        pointer-events: none;
        background: linear-gradient(135deg, rgba(37,99,235,.1), transparent 45%, rgba(251,146,60,.11));
      }

      .landing-cta-panel > * {
        position: relative;
      }

      .landing-cta-panel h3 {
        margin: .2rem 0 .5rem 0;
        color: var(--ink);
        font-size: 1.45rem;
        letter-spacing: -.045em;
      }

      .landing-cta-label {
        display: inline-flex;
        margin-bottom: .4rem;
        color: var(--blue-dark);
        font-size: .76rem;
        font-weight: 900;
        letter-spacing: .08em;
        text-transform: uppercase;
      }

      .landing-cta-panel p {
        margin: 0 0 1rem 0;
        color: var(--muted);
        font-size: .96rem;
        line-height: 1.55;
      }

      .landing-cta-button {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        min-height: 3.25rem;
        border-radius: 1rem;
        background:
          linear-gradient(135deg, #2563eb 0%, #4f46e5 45%, #f97316 125%);
        color: #ffffff !important;
        font-weight: 850;
        text-decoration: none !important;
        box-shadow: 0 12px 28px rgba(37, 99, 235, .24);
        transition: transform .12s ease, background .12s ease;
      }

      .landing-cta-button:hover {
        background:
          linear-gradient(135deg, #1d4ed8 0%, #4338ca 44%, #ea580c 125%);
        transform: translateY(-1px);
      }

      @media (max-width: 860px) {
        .landing-hero {
          height: auto;
          min-height: calc(100vh - 1.35rem);
          grid-template-columns: 1fr;
        }
      }

      .section-title {
        margin: 1.8rem 0 .7rem 0;
        color: var(--ink);
        letter-spacing: -.03em;
      }

      .st-key-workspace_page {
        max-width: 1180px;
        margin: 0 auto;
        padding: clamp(1.25rem, 2.4vw, 2rem);
      }

      .workspace-header {
        margin: .4rem 0 1.1rem 0;
        padding: 1.35rem 1.45rem;
        border: 1px solid #dbeafe;
        border-radius: 1.35rem;
        background:
          radial-gradient(circle at 88% 10%, rgba(251,146,60,.13), transparent 30%),
          linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
      }

      .workspace-header h1 {
        margin: .35rem 0 .3rem 0;
        color: var(--ink);
        font-size: clamp(1.8rem, 3vw, 2.6rem);
        letter-spacing: -.05em;
      }

      .workspace-header p {
        margin: 0;
        color: var(--muted);
        max-width: 720px;
        line-height: 1.55;
      }

      .back-link {
        display: inline-flex;
        margin-bottom: .85rem;
        color: var(--blue-dark);
        font-weight: 750;
        text-decoration: none !important;
        font-size: .92rem;
      }

      .stage-card, .panel, .preview-card, .result-card {
        border: 1px solid var(--line);
        border-radius: 1.25rem;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
      }

      .stage-card {
        min-height: 145px;
        padding: 1.12rem;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
      }

      .stage-index {
        color: var(--blue);
        font-size: .78rem;
        font-weight: 900;
        letter-spacing: .08em;
        text-transform: uppercase;
      }

      .stage-card h3 {
        margin: .38rem 0 .42rem 0;
        color: var(--ink);
        font-size: 1.06rem;
      }

      .stage-card p {
        margin: 0;
        color: var(--muted);
        font-size: .93rem;
        line-height: 1.5;
      }

      .panel {
        padding: 1.2rem;
        background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
        margin-bottom: 1rem;
      }

      .preview-card {
        padding: 1rem;
        background: #fbfdff;
      }

      .result-card {
        padding: 1.05rem 1.15rem;
        background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
        border-color: #dbeafe;
      }

      .result-card h3 {
        margin: .1rem 0 .3rem 0;
        color: var(--ink);
      }

      .result-card p {
        color: #475569;
        margin-bottom: 0;
        line-height: 1.55;
      }

      .small-muted {
        color: var(--muted);
        font-size: .9rem;
      }

      .compact-meta-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .75rem;
        margin: .85rem 0 1rem 0;
      }

      .compact-meta-card {
        min-width: 0;
        border: 1px solid #e2e8f0;
        border-radius: 1rem;
        padding: .78rem .85rem;
        background: #ffffff;
      }

      .compact-meta-label {
        color: var(--muted);
        font-size: .74rem;
        font-weight: 800;
        letter-spacing: .055em;
        text-transform: uppercase;
        margin-bottom: .28rem;
      }

      .compact-meta-value {
        color: var(--ink);
        font-size: .98rem;
        font-weight: 800;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .compact-meta-value.file-name {
        font-size: .9rem;
        font-weight: 750;
      }

      .schema-chip {
        display: inline-block;
        margin: .2rem .35rem .2rem 0;
        padding: .35rem .55rem;
        border-radius: .65rem;
        background: #f1f5f9;
        color: #334155;
        font-size: .84rem;
        font-weight: 650;
      }

      div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 1rem;
        overflow: hidden;
      }

      @media (max-width: 900px) {
        .compact-meta-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def ensure_page():
    query_page = st.query_params.get("page")
    if query_page in {"landing", "jd", "ranker"}:
        st.session_state.page = query_page
    elif "page" not in st.session_state:
        st.session_state.page = "landing"


def go_to(page):
    st.session_state.page = page
    st.query_params["page"] = page


def candidate_suffix(filename):
    path = Path(filename)
    if path.suffix == ".gz":
        return ".jsonl.gz"
    return path.suffix or ".json"


def rows_to_csv(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["candidate_id", "rank", "score", "reasoning"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "candidate_id": row["candidate_id"],
                "rank": row["rank"],
                "score": row["score"],
                "reasoning": row["reasoning"],
            }
        )
    return buffer.getvalue()


def parse_preview_records(file_bytes, filename, limit=8):
    suffix = candidate_suffix(filename)
    if suffix == ".jsonl.gz":
        text = gzip.decompress(file_bytes).decode("utf-8")
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        text = file_bytes.decode("utf-8")
        stripped = text.lstrip()
        if stripped.startswith("["):
            records = json.loads(text)
        else:
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return records[:limit], len(records)


def current_role(candidate):
    history = candidate.get("career_history", [])
    for role in history:
        if role.get("is_current"):
            return role
    return history[0] if history else {}


def format_bool(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return ""


def preview_value(candidate, field):
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})
    role = current_role(candidate)

    values = {
        "candidate_id": candidate.get("candidate_id", ""),
        "current_title": profile.get("current_title", ""),
        "headline": profile.get("headline", ""),
        "location": profile.get("location", ""),
        "country": profile.get("country", ""),
        "years_experience": profile.get("years_of_experience", ""),
        "current_company": profile.get("current_company", ""),
        "current_industry": profile.get("current_industry", ""),
        "top_skills": ", ".join(skill.get("name", "") for skill in skills[:4]),
        "skill_count": len(skills),
        "current_role_title": role.get("title", ""),
        "current_role_company": role.get("company", ""),
        "current_role_duration": role.get("duration_months", ""),
        "notice_period": signals.get("notice_period_days", ""),
        "response_rate": signals.get("recruiter_response_rate", ""),
        "open_to_work": format_bool(signals.get("open_to_work_flag")),
        "profile_completeness": signals.get("profile_completeness_score", ""),
        "verified_email": format_bool(signals.get("verified_email")),
    }
    return values.get(field, "")


def flatten_preview(candidate, selected_labels):
    return {
        label: preview_value(candidate, PREVIEW_COLUMN_OPTIONS[label])
        for label in selected_labels
    }


def render_compact_meta(items):
    columns = st.columns(len(items))
    for column, (label, value, _extra_class) in zip(columns, items):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"**{value}**")


@st.cache_data(show_spinner=False)
def rank_file(file_bytes, filename, jd_text, top_n, artifact_limit):
    uploaded_path = None
    artifact_path = None
    jd_profile = build_jd_understanding(jd_text)
    try:
        suffix = candidate_suffix(filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            uploaded_path = temp_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as artifact_file:
            artifact_path = artifact_file.name

        compute_precompute_artifact(
            uploaded_path,
            output_path=artifact_path,
            artifact_limit=artifact_limit,
            progress_every=0,
            quiet=True,
            jd_profile=jd_profile,
        )
        return rank_candidates(
            uploaded_path,
            top_n=top_n,
            heap_size=max(artifact_limit, top_n),
            progress_every=0,
            quiet=True,
            precompute_artifact=artifact_path,
            jd_profile=jd_profile,
        )
    finally:
        for path in (uploaded_path, artifact_path):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass


def load_sample_bytes():
    with open(SAMPLE_CANDIDATES, "rb") as file:
        return file.read()


def load_default_jd_text():
    if DEFAULT_JD_PATH.exists():
        return strip_participant_note(DEFAULT_JD_PATH.read_text(encoding="utf-8"))
    return ""


def strip_participant_note(jd_text):
    if PARTICIPANT_NOTE_HEADING in jd_text:
        return jd_text.split(PARTICIPANT_NOTE_HEADING, 1)[0].rstrip()
    return jd_text


def render_topbar(show_back=False):
    if show_back:
        st.markdown(
            '<a class="back-link" href="?page=landing" target="_self">← Back to landing</a>',
            unsafe_allow_html=True,
        )


def render_stage_cards():
    cards = [
        ("00", "JD understanding", "The role mandate, must-haves, preferences, and risks are encoded first."),
        ("01", "Semantic retrieval", "BM25-style matching over JD-specific evidence concepts."),
        ("02", "Coverage shortlist", "Fixed JD coverage weights focus the semantic shortlist."),
        ("03", "Evidence scoring", "Roles, skills, trust, logistics, and risk penalties shape fit."),
        ("04", "Grounded reasoning", "Each ranked row gets one concise fact-backed sentence."),
    ]
    columns = st.columns(5)
    for column, (number, title, body) in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="stage-card">
                  <div class="stage-index">Stage {number}</div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_landing():
    st.markdown(
        """
        <div class="landing-hero">
          <div class="landing-hero-copy">
            <div class="landing-brand">jinsil<span>.</span></div>
            <h1>Candidate ranking that shows its work.</h1>
            <p>
              Paste a JD, upload a candidate file, and Jinsil turns it into a ranked shortlist using semantic
              retrieval, fixed JD coverage scoring, deterministic scoring, and
              transparent one-sentence explanations grounded only in profile evidence.
              It learns from the JD, not from the uploaded candidate data.
            </p>
            <div class="landing-pill-row">
              <div class="landing-pill">Upload small test sets</div>
              <div class="landing-pill">Preview before ranking</div>
              <div class="landing-pill">Download CSV output</div>
              <div class="landing-pill">No network calls during scoring</div>
              <div class="landing-pill">No candidate-data training</div>
            </div>
          </div>
          <div class="landing-cta-panel">
            <div class="landing-cta-label">Live sandbox</div>
            <h3>Test the ranker</h3>
            <p>Open the workspace to paste a JD, upload candidates, preview the dataset, rank it, and export a CSV.</p>
            <a class="landing-cta-button" href="?page=jd" target="_self">Start with a JD</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_controls():
    st.markdown(
        """
        <div class="workspace-header">
          <h1>Understand the JD, then rank candidates.</h1>
          <p>The app builds a deterministic JD profile before candidates are scanned; uploaded candidate data is only retrieved, scored, and ranked, never used to update rules, weights, or model parameters.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        left, right = st.columns([1.65, 1])
        with left:
            uploaded_file = st.file_uploader(
                "Upload candidate file",
                type=sorted(SUPPORTED_EXTENSIONS),
                help="Use the same schema as sample_candidates.json.",
            )
            use_sample = st.toggle("Use bundled sample instead", value=uploaded_file is None)
            st.caption("A preview appears below before ranking runs.")
        with right:
            top_n = st.slider("Candidates to return", 5, 100, 20, 5)
            artifact_limit = st.slider(
                "Shortlist size",
                25,
                500,
                100,
                25,
                help="Keep hosted uploads fast while preserving the same two-stage architecture.",
            )
    return uploaded_file, use_sample, top_n, artifact_limit


def initialize_jd_draft():
    if "jd_draft" not in st.session_state:
        st.session_state.jd_draft = load_default_jd_text()


def render_jd_editor():
    initialize_jd_draft()
    uploaded_jd = st.file_uploader(
        "Upload JD file",
        type=["txt", "md"],
        key="jd_upload",
        help="Optional. You can also paste or edit the JD below.",
    )
    if uploaded_jd is not None:
        uploaded_text = uploaded_jd.getvalue().decode("utf-8", errors="replace")
        if st.button("Use uploaded JD", use_container_width=True):
            st.session_state.jd_draft = strip_participant_note(uploaded_text)
            st.rerun()

    preview_tab, edit_tab = st.tabs(["Rendered Markdown", "Edit JD"])
    with preview_tab:
        with st.container(border=True):
            st.markdown(st.session_state.jd_draft)
        st.caption("Use the Edit JD tab to change this rendered Markdown before processing.")
    with edit_tab:
        st.text_area(
            "JD Markdown",
            key="jd_draft",
            height=420,
            help="Edit the JD here, then process it to move to candidate upload.",
        )

    return st.session_state.jd_draft


def render_jd_page():
    with st.container(key="workspace_page"):
        render_topbar(show_back=True)
        st.markdown(
            """
            <div class="workspace-header">
              <h1>Step 1: Process the JD.</h1>
              <p>Render, review, and edit the JD first. The participant-only hackathon note is not shown in this app, but its intent is encoded in the ranking logic.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        jd_text = render_jd_editor()

        can_continue = bool(jd_text.strip())
        if st.button("Process JD and continue", type="primary", use_container_width=True, disabled=not can_continue):
            jd_profile = build_jd_understanding(jd_text)
            st.session_state.processed_jd_text = jd_text
            st.session_state.processed_jd_profile = jd_profile
            go_to("ranker")
            st.rerun()


def render_processed_jd_summary(jd_text):
    jd_profile = st.session_state.get("processed_jd_profile") or build_jd_understanding(jd_text)
    st.markdown('<h3 class="section-title">Processed JD</h3>', unsafe_allow_html=True)
    render_jd_overview(jd_profile)
    with st.expander("Detailed JD analysis", expanded=False):
        render_jd_understanding(jd_text)
    return jd_profile


def sorted_terms(values, limit=None):
    if isinstance(values, dict):
        ordered = sorted(values, key=lambda term: (-values[term], term))
    else:
        ordered = sorted(values)
    return ordered[:limit] if limit else ordered


def term_text(values, limit=10, fallback="No explicit signals detected."):
    terms = sorted_terms(values, limit)
    return ", ".join(terms) if terms else fallback


def jd_signal_counts(jd_profile):
    must_have = jd_profile["must_have_evidence"]
    positives = jd_profile["strong_positive_evidence"]
    negatives = jd_profile["negative_evidence"]
    return {
        "technical": len(must_have["technical_terms"]),
        "core": len(must_have["retrieval_ranking_terms"]),
        "evaluation": len(must_have["evaluation_terms"]),
        "production": len(must_have["production_terms"]),
        "product": len(positives["product_ownership_terms"]),
        "leadership": len(positives["leadership_terms"]),
        "adjacent": len(positives["adjacent_terms"]),
        "negative": (
            len(negatives["non_target_titles"])
            + len(negatives["consulting_only_companies"])
            + len(negatives["research_without_shipping"])
            + len(negatives["non_target_ai_domains"])
        ),
    }


def render_jd_overview(jd_profile):
    retrieval_terms = jd_retrieval_terms(jd_profile)
    ideal = jd_profile["ideal_profile"]
    logistics = jd_profile["logistics"]
    counts = jd_signal_counts(jd_profile)
    preferred_locations = logistics["preferred_locations"]

    render_compact_meta(
        [
            ("Role detected", jd_profile["role"], ""),
            ("Experience band", ideal["experience_years"], ""),
            ("Ranking concepts", len(retrieval_terms), ""),
            ("Preferred locations", len(preferred_locations) or "Flexible", ""),
        ]
    )

    left, right = st.columns([1.25, 1])
    with left:
        with st.container(border=True):
            st.caption("Qualitative interpretation")
            st.write(jd_profile["core_mandate"])
            st.write(
                "The ranker will prioritize candidates whose career history proves the "
                "role's main responsibilities, then use skills, seniority, location, "
                "availability, and trust signals to separate strong matches from weak "
                "keyword matches."
            )
    with right:
        with st.container(border=True):
            st.caption("Quantitative signal map")
            st.write(
                f"{counts['technical']} technical terms, {counts['core']} core domain terms, "
                f"{counts['evaluation']} evaluation terms, {counts['production']} production terms, "
                f"{counts['product']} product/workflow terms, and {counts['negative']} explicit risk terms."
            )
            st.progress(min(len(retrieval_terms) / 80.0, 1.0))
            st.caption("Concept coverage depth")


def render_jd_understanding(jd_text):
    jd_profile = build_jd_understanding(jd_text)
    retrieval_terms = jd_retrieval_terms(jd_profile)
    counts = jd_signal_counts(jd_profile)
    ideal = jd_profile["ideal_profile"]
    logistics = jd_profile["logistics"]
    negatives = jd_profile["negative_evidence"]

    st.markdown('<h3 class="section-title">JD Understanding</h3>', unsafe_allow_html=True)
    render_compact_meta(
        [
            ("Role detected", jd_profile["role"], ""),
            ("Experience band", ideal["experience_years"], ""),
            ("Ranking concepts", len(retrieval_terms), ""),
            ("Risk signals", counts["negative"], ""),
        ]
    )

    blueprint_tab, signals_tab, risk_tab = st.tabs(
        ["Fit Blueprint", "Evidence Signals", "Risk & Logistics"]
    )
    with blueprint_tab:
        left, right = st.columns([1.15, 1])
        with left:
            with st.container(border=True):
                st.caption("Role mandate")
                st.write(jd_profile["core_mandate"])
                st.caption("Ideal proof")
                st.write(ideal["proof"])
        with right:
            with st.container(border=True):
                st.caption("How candidates will be separated")
                st.write(
                    "Career evidence and current-role alignment carry more weight than "
                    "isolated skill keywords; behavioral availability and profile trust "
                    "then determine whether a strong-on-paper candidate is realistically "
                    "hireable."
                )
                st.caption("Target title evidence")
                st.write(term_text(ideal["target_title_terms"], limit=8))

    with signals_tab:
        columns = st.columns(4)
        signal_cards = [
            ("Technical", counts["technical"], jd_profile["must_have_evidence"]["technical_terms"]),
            ("Core Domain", counts["core"], jd_profile["must_have_evidence"]["retrieval_ranking_terms"]),
            ("Evaluation", counts["evaluation"], jd_profile["must_have_evidence"]["evaluation_terms"]),
            ("Production", counts["production"], jd_profile["must_have_evidence"]["production_terms"]),
        ]
        for column, (label, count, terms) in zip(columns, signal_cards):
            with column:
                with st.container(border=True):
                    st.caption(label)
                    st.markdown(f"**{count} signals**")
                    st.write(term_text(terms, limit=7))

        columns = st.columns(3)
        positive_cards = [
            (
                "Product / Workflow",
                counts["product"],
                jd_profile["strong_positive_evidence"]["product_ownership_terms"],
            ),
            (
                "Leadership",
                counts["leadership"],
                jd_profile["strong_positive_evidence"]["leadership_terms"],
            ),
            (
                "Adjacent Support",
                counts["adjacent"],
                jd_profile["strong_positive_evidence"]["adjacent_terms"],
            ),
        ]
        for column, (label, count, terms) in zip(columns, positive_cards):
            with column:
                with st.container(border=True):
                    st.caption(label)
                    st.markdown(f"**{count} signals**")
                    st.write(term_text(terms, limit=7))

    with risk_tab:
        left, right = st.columns([1, 1])
        with left:
            with st.container(border=True):
                st.caption("Logistics interpretation")
                locations = logistics["preferred_locations"]
                st.write(
                    f"Preferred locations: {', '.join(locations) if locations else 'flexible / not explicit'}."
                )
                st.write(logistics["notice_period"])
                st.write(logistics["availability"])
        with right:
            with st.container(border=True):
                st.caption("Down-rank logic")
                risk_terms = (
                    set(negatives["non_target_titles"])
                    | set(negatives["consulting_only_companies"])
                    | set(negatives["research_without_shipping"])
                    | set(negatives["non_target_ai_domains"])
                )
                st.write(term_text(risk_terms, limit=12, fallback="No explicit named risk terms."))
                st.write(
                    "The ranker still penalizes unrelated evidence, keyword stuffing, "
                    "stale activity, weak response behavior, and low profile trust."
                )

    with st.expander("Operational guarantee"):
        st.write(
            "The processed JD becomes a fixed scoring profile before candidates are uploaded "
            "or ranked. Candidate data is only retrieved, scored, and ranked; it never updates "
            "rules, weights, or model parameters."
        )
    return jd_profile


def get_active_file(uploaded_file, use_sample):
    if uploaded_file is not None:
        return uploaded_file.getvalue(), uploaded_file.name
    if use_sample:
        return load_sample_bytes(), SAMPLE_CANDIDATES
    return None, None


def render_dataset_preview(file_bytes, filename):
    if not file_bytes:
        st.info("Upload a file or choose the bundled sample to preview candidates.")
        return

    st.markdown('<h3 class="section-title">Dataset Preview</h3>', unsafe_allow_html=True)
    try:
        records, total = parse_preview_records(file_bytes, filename)
    except Exception as exc:
        st.error(f"Could not preview `{filename}`: {exc}")
        return

    render_compact_meta(
        [
            ("Detected records", total, ""),
            ("Preview rows", len(records), ""),
            ("File", filename, "file-name"),
            ("Type", candidate_suffix(filename).replace(".", "").upper(), ""),
        ]
    )

    selected_labels = st.multiselect(
        "Choose preview columns",
        options=list(PREVIEW_COLUMN_OPTIONS),
        default=DEFAULT_PREVIEW_COLUMNS,
        max_selections=6,
        help="Pick up to 6 fields to inspect before ranking.",
    )
    if not selected_labels:
        st.warning("Select at least one preview column.")
        return

    preview_rows = [flatten_preview(record, selected_labels) for record in records]

    if records:
        first = records[0]
        chips = []
        for key in ("profile", "skills", "career_history", "redrob_signals"):
            if key in first:
                chips.append(f'<span class="schema-chip">{key}</span>')
        if chips:
            st.markdown("".join(chips), unsafe_allow_html=True)
    st.dataframe(preview_rows, use_container_width=True, hide_index=True)


def render_results(rows, filename):
    csv_data = rows_to_csv(rows)
    top = rows[0] if rows else None

    st.markdown('<h3 class="section-title">Ranking Results</h3>', unsafe_allow_html=True)
    render_compact_meta(
        [
            ("Returned", len(rows), ""),
            ("Top score", top["score"] if top else "-", ""),
            ("Source file", filename, "file-name"),
            ("Download", "Ready", ""),
        ]
    )

    if top:
        st.markdown(
            f"""
            <div class="result-card">
              <div class="small-muted">Top recommendation</div>
              <h3>{top['candidate_id']} · score {top['score']}</h3>
              <p>{top['reasoning']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    table_rows = [
        {
            "rank": row["rank"],
            "candidate_id": row["candidate_id"],
            "score": row["score"],
            "reasoning": row["reasoning"],
        }
        for row in rows
    ]
    table_tab, reason_tab, download_tab = st.tabs(["Ranked table", "Reasoning", "Download"])
    with table_tab:
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    with reason_tab:
        for row in rows[: min(len(rows), 10)]:
            with st.expander(f"Rank {row['rank']} · {row['candidate_id']} · {row['score']}"):
                st.write(row["reasoning"])
    with download_tab:
        st.download_button(
            "Download ranked CSV",
            data=csv_data,
            file_name="ranked_candidates.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("Columns match the challenge format: candidate_id, rank, score, reasoning.")


def render_ranker():
    with st.container(key="workspace_page"):
        st.markdown('<a class="back-link" href="?page=jd" target="_self">← Back to JD</a>', unsafe_allow_html=True)
        jd_text = st.session_state.get("processed_jd_text")
        if not jd_text:
            st.warning("Process a JD before uploading candidates.")
            if st.button("Go to JD step", type="primary"):
                go_to("jd")
                st.rerun()
            return
        jd_profile = render_processed_jd_summary(jd_text)
        uploaded_file, use_sample, top_n, artifact_limit = render_controls()
        file_bytes, filename = get_active_file(uploaded_file, use_sample)
        render_dataset_preview(file_bytes, filename)

        run_disabled = file_bytes is None or not jd_text.strip()
        run = st.button("Run ranking", type="primary", use_container_width=True, disabled=run_disabled)
        if not run:
            st.info("Review the JD understanding and dataset preview, then run the ranker.")
            return

        with st.spinner("Ranking candidates with the JD-first no-training pipeline..."):
            try:
                rows = rank_file(file_bytes, filename, jd_text, top_n, artifact_limit)
            except Exception as exc:
                st.error(f"Ranking failed: {exc}")
                return

        st.success(f"Ranked {len(rows)} candidates from `{filename}` for `{jd_profile['role']}`.")
        render_results(rows, filename)


def main():
    ensure_page()
    if st.session_state.page == "ranker":
        render_ranker()
    elif st.session_state.page == "jd":
        render_jd_page()
    else:
        render_landing()


if __name__ == "__main__":
    main()
