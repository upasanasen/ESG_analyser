import base64
import os
import re

import fitz
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config + design system
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ESG Analyser — CSRD screening suite",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

GREEN = "#0C7C43"       # primary deep green
EMERALD = "#17A05F"     # data green
MINT = "#E7F5EC"        # soft panel
INK = "#10201A"
MUTED = "#59635C"
TRACK = "#EDF1EE"
AMBER = "#E0BC6B"


def load_css(path: str = "style.css") -> None:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css()

# ---------------------------------------------------------------------------
# Rule libraries (unchanged)
# ---------------------------------------------------------------------------

FRAMEWORK_KEYWORDS = {
    "GRI": [
        "gri", "material topics", "stakeholder engagement", "general disclosures",
        "management approach", "content index", "materiality", "disclosure"
    ],
    "ESRS / CSRD": [
        "esrs", "csrd", "double materiality", "impact materiality", "financial materiality",
        "value chain", "e1", "s1", "g1", "sustainability statement"
    ],
    "TCFD": [
        "tcfd", "scenario analysis", "climate risk", "governance", "strategy",
        "risk management", "metrics and targets", "physical risk", "transition risk"
    ],
    "GHG Protocol": [
        "ghg protocol", "scope 1", "scope 2", "scope 3", "greenhouse gas",
        "emissions", "market-based", "location-based", "carbon dioxide equivalent", "co2e"
    ],
    "SDGs": [
        "sdg", "sustainable development goals", "un global compact", "sdg 13",
        "sdg 12", "sdg 8", "sdg 5"
    ],
}

ESG_PILLARS = {
    "Environment": [
        "emissions", "energy", "renewable", "water", "waste", "biodiversity",
        "pollution", "recycling", "resource efficiency", "climate"
    ],
    "Social": [
        "employees", "health and safety", "diversity", "inclusion", "human rights",
        "labour", "training", "community", "equity", "wellbeing"
    ],
    "Governance": [
        "board", "ethics", "anti-corruption", "compliance", "whistleblowing",
        "risk committee", "remuneration", "audit", "policy", "oversight"
    ],
    "Climate Risk": [
        "net zero", "transition plan", "1.5", "science-based", "scenario analysis",
        "climate risk", "physical risk", "transition risk", "carbon price", "decarbonisation"
    ],
    "Supply Chain": [
        "supplier", "supply chain", "procurement", "value chain", "due diligence",
        "supplier code", "category 1", "category 11", "category 15", "scope 3"
    ],
}

GAP_CHECKS = [
    ("Scope 3 data incomplete", "scope 3", "High", "Disclose material Scope 3 categories, calculation method, boundary, and assumptions."),
    ("Double materiality missing", "double materiality", "High", "Add impact and financial materiality assessment with stakeholder input and methodology."),
    ("Climate transition plan missing", "transition plan", "Medium", "Explain how climate targets will be achieved through CAPEX, operations, and accountable owners."),
    ("Interim climate targets missing", "2030", "Medium", "Add near-term targets, not only long-term net-zero ambition."),
    ("Human rights due diligence limited", "human rights", "Medium", "Explain due diligence process, salient risks, findings, and remediation actions."),
    ("Governance oversight not clear", "board oversight", "Medium", "Clarify board/committee responsibilities for sustainability and climate risk."),
    ("Biodiversity assessment missing", "biodiversity", "Low", "Assess biodiversity impacts, dependencies, locations, and mitigation actions where material."),
]

GREENWASHING_TERMS = [
    "eco-friendly", "environmentally friendly", "carbon neutral", "climate neutral",
    "net zero", "green product", "best-in-class", "industry leading",
    "most sustainable", "climate positive", "zero impact", "nature positive"
]

EVIDENCE_TERMS = [
    "%", "tonnes", "tco2e", "co2e", "scope 1", "scope 2", "scope 3",
    "baseline", "verified", "assurance", "certified", "iso", "sbti",
    "methodology", "audit", "limited assurance", "reasonable assurance"
]

ESRS_TOPICS = {
    "ESRS E1 Climate Change": ["climate", "emissions", "scope 1", "scope 2", "scope 3", "transition plan"],
    "ESRS E2 Pollution": ["pollution", "air emissions", "water pollution", "hazardous"],
    "ESRS E3 Water and Marine Resources": ["water", "water withdrawal", "water consumption", "marine"],
    "ESRS E4 Biodiversity": ["biodiversity", "ecosystem", "habitat", "nature"],
    "ESRS E5 Resource Use and Circular Economy": ["circular", "recycling", "waste", "resource use"],
    "ESRS S1 Own Workforce": ["employees", "workforce", "health and safety", "training", "diversity"],
    "ESRS S2 Workers in Value Chain": ["value chain workers", "supplier workers", "labour rights"],
    "ESRS S3 Affected Communities": ["communities", "affected communities", "local community"],
    "ESRS S4 Consumers and End-users": ["consumers", "end-users", "customer safety", "privacy"],
    "ESRS G1 Business Conduct": ["anti-corruption", "ethics", "whistleblowing", "business conduct"],
}

# ---------------------------------------------------------------------------
# Analysis functions (unchanged)
# ---------------------------------------------------------------------------

def extract_pdf_text(uploaded_file) -> str:
    data = uploaded_file.read()
    doc = fitz.open(stream=data, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def keyword_score(text: str, keywords: list) -> int:
    matched = sum(1 for keyword in keywords if keyword.lower() in text)
    return round((matched / len(keywords)) * 100) if keywords else 0


def grade_from_score(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def maturity_band(score: int) -> str:
    if score >= 70:
        return "Advanced"
    if score >= 40:
        return "Developing"
    return "Nascent"


def calculate_scores(text: str):
    framework_scores = {name: keyword_score(text, words) for name, words in FRAMEWORK_KEYWORDS.items()}
    pillar_scores = {name: keyword_score(text, words) for name, words in ESG_PILLARS.items()}
    return framework_scores, pillar_scores


def build_gap_table(text: str) -> pd.DataFrame:
    rows = []
    for gap, required_term, severity, recommendation in GAP_CHECKS:
        if required_term.lower() not in text:
            rows.append({
                "Severity": severity,
                "Disclosure gap": gap,
                "Recommendation": recommendation,
            })
    return pd.DataFrame(rows)


def surrounding_window(text: str, term: str, window: int = 180) -> str:
    idx = text.find(term.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(term) + window)
    return text[start:end]


def detect_greenwashing(text: str) -> pd.DataFrame:
    rows = []
    for term in GREENWASHING_TERMS:
        if term in text:
            context = surrounding_window(text, term)
            has_evidence = any(evidence in context for evidence in EVIDENCE_TERMS)
            rows.append({
                "Risk": "Medium" if has_evidence else "High",
                "Claim detected": term,
                "Reason": "Some supporting evidence appears nearby." if has_evidence else "Claim appears without clear nearby evidence, baseline, methodology, or verification.",
                "Fix": "Add quantified evidence, baseline, methodology, reporting boundary, and assurance reference."
            })
    return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()


def esrs_coverage(text: str) -> pd.DataFrame:
    rows = []
    for topic, keywords in ESRS_TOPICS.items():
        score = keyword_score(text, keywords)
        if score >= 60:
            status = "Disclosed"
        elif score >= 25:
            status = "Partial"
        else:
            status = "Missing"
        rows.append({"ESRS topic": topic, "Status": status, "Coverage score": score})
    return pd.DataFrame(rows)


def create_template_summary(overall, csrd, risk_level, strongest, weakest, gap_count, flag_count):
    return (
        f"The uploaded sustainability report shows an estimated ESG disclosure maturity score of {overall}/100. "
        f"The strongest disclosure area is {strongest}, while {weakest} appears to require the most improvement. "
        f"Estimated CSRD/ESRS readiness is {csrd}%, with {gap_count} priority disclosure gaps and {flag_count} potential greenwashing claim(s) detected. "
        "This is a rule-based screening result designed to highlight disclosure quality, not a formal assurance or audit opinion."
    )


def build_recommendations(gaps_df, framework_scores, greenwashing_df):
    recommendations = []
    if not gaps_df.empty:
        recommendations.extend(gaps_df["Recommendation"].head(4).tolist())

    weak_frameworks = [fw for fw, score in framework_scores.items() if score < 50]
    if weak_frameworks:
        recommendations.append(f"Improve weak framework coverage for: {', '.join(weak_frameworks)}.")

    if not greenwashing_df.empty:
        recommendations.append("Create a green-claims evidence register linking every sustainability claim to data, methodology, boundary, and assurance evidence.")

    recommendations.append("Add a management action plan with owners, timelines, KPIs, and evidence sources for each priority ESG gap.")
    return recommendations[:6]

# ---------------------------------------------------------------------------
# Charts (restyled: light, green, Hanken Grotesk)
# ---------------------------------------------------------------------------

def plot_radar(pillar_scores):
    categories = list(pillar_scores.keys())
    values = list(pillar_scores.values())

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(23,160,95,0.18)",
        line=dict(color=EMERALD, width=2.5),
        marker=dict(color=GREEN, size=6),
        name="Score",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="#E9EEEB", linecolor="#E4EAE6",
                tickfont=dict(color="#8A968E", size=10),
            ),
            angularaxis=dict(
                gridcolor="#E4EAE6", linecolor="#E4EAE6",
                tickfont=dict(color=MUTED, size=12),
            ),
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk", color=MUTED),
        height=360,
        margin=dict(l=50, r=50, t=30, b=30),
    )
    return fig


def plot_frameworks(framework_scores):
    names = list(framework_scores.keys())[::-1]
    values = list(framework_scores.values())[::-1]
    colors = [EMERALD if v >= 50 else AMBER for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker=dict(color=colors, cornerradius=5),
        text=[f"{v}%" for v in values],
        textposition="outside",
        textfont=dict(family="Hanken Grotesk", size=13, color=INK),
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 108], gridcolor=TRACK, zeroline=False,
                   tickfont=dict(color="#8A968E", size=11)),
        yaxis=dict(tickfont=dict(color=INK, size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk", color=MUTED),
        height=360,
        margin=dict(l=10, r=20, t=30, b=30),
        bargap=0.45,
    )
    return fig

# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------

def metric_card(label: str, value_html: str, note: str, extra_class: str = ""):
    st.markdown(
        f'<div class="metric-card {extra_class}">'
        f'<div class="metric-label">{label}</div>'
        f'{value_html}'
        f'<div class="metric-note">{note}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def ring_html(score: int) -> str:
    deg = round(score * 3.6)
    return (
        f'<div class="ring" style="background:conic-gradient({EMERALD} {deg}deg, #CFE7D8 {deg}deg 360deg);">'
        f'<div class="ring-hole"><span class="ring-num">{score}</span>'
        f'<span class="ring-den">/100</span></div></div>'
    )


def bar_html(pct: int) -> str:
    return f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;"></div></div>'


def hero_bg_style() -> str:
    """Use assets/hero.jpg if present, else a deep-green gradient."""
    path = "assets/hero.jpg"
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return (
            "background-image: linear-gradient(180deg, rgba(8,26,19,.35), "
            "rgba(8,26,19,.6) 60%, rgba(8,26,19,.35)), "
            f"url(data:image/jpeg;base64,{b64});"
        )
    return (
        "background-image: radial-gradient(circle at 20% 0%, rgba(23,160,95,.5), transparent 50%), "
        "linear-gradient(135deg, #0B4A2C, #0C7C43);"
    )

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="side-logo">'
        '<div class="side-logo-mark">E</div>'
        '<div><div class="side-logo-name">ESG Analyser</div>'
        '<div class="side-logo-sub">CSRD screening suite</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-heading">Screening modules</div>', unsafe_allow_html=True)
    for module in [
        "ESG pillar maturity",
        "CSRD / ESRS readiness",
        "Framework coverage",
        "Disclosure gaps",
        "Greenwashing review",
        "Executive summary",
    ]:
        st.markdown(
            f'<div class="side-item"><span class="side-dot"></span>{module}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="side-note">'
        '<div class="side-note-title">Rule-based engine</div>'
        '<div class="side-note-body">Screening output — not a formal audit or assurance opinion. '
        'No API key, quota, or billing needed.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Hero + uploader
# ---------------------------------------------------------------------------

st.markdown(
    f'<div class="hero" style="{hero_bg_style()}">'
    '<div class="eyebrow">CSRD readiness &amp; greenwashing scanner</div>'
    '<h1>Screen a sustainability<br>report in one upload.</h1>'
    '<p>Upload a report PDF and get an ESG screening dashboard covering CSRD/ESRS readiness, '
    'framework coverage, disclosure gaps, and greenwashing risk.</p>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tag-row">'
    '<span class="tag">CSRD / ESRS</span><span class="tag">GRI</span>'
    '<span class="tag">TCFD</span><span class="tag">GHG Protocol</span>'
    '<span class="tag">Greenwashing risk</span>'
    '</div>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a sustainability report PDF",
    type=["pdf"],
    help="Upload a text-based PDF. Scanned/image-based PDFs may not extract correctly.",
    label_visibility="collapsed",
)

if uploaded_file is None:
    col1, col2, col3 = st.columns(3)
    steps = [
        ("01", "Upload", "Add a sustainability or ESG report PDF."),
        ("02", "Scan", "Rule-based checks across ESG, CSRD, GRI, TCFD & GHG."),
        ("03", "Improve", "Use the dashboard to close reporting gaps."),
    ]
    for col, (num, title, body) in zip([col1, col2, col3], steps):
        with col:
            st.markdown(
                f'<div class="step-card"><div class="step-num">{num}</div>'
                f'<div class="step-title">{title}</div>'
                f'<div class="step-body">{body}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown(
        '<div class="footer-note">Processed in-session. Reports are not stored or shared. '
        'Rule-based engine — no API required.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Scan (with progress status)
# ---------------------------------------------------------------------------

with st.status("Scanning report…", expanded=True) as status:
    st.write("Extracting text (PyMuPDF)")
    try:
        raw_text = extract_pdf_text(uploaded_file)
    except Exception as exc:
        status.update(label="Scan failed", state="error")
        st.error(f"Could not read the PDF: {exc}")
        st.stop()

    if len(raw_text.strip()) < 300:
        status.update(label="Scan failed", state="error")
        st.error("The report text could not be extracted properly. This may be a scanned/image-based PDF. Try a text-based PDF.")
        st.stop()

    st.write("Matching ESG & CSRD/ESRS terms")
    text = clean_text(raw_text)
    framework_scores, pillar_scores = calculate_scores(text)

    st.write("Scoring framework coverage (GRI, TCFD, GHG)")
    gaps_df = build_gap_table(text)
    esrs_df = esrs_coverage(text)

    st.write("Detecting greenwashing signals")
    greenwashing_df = detect_greenwashing(text)

    status.update(label=f"Scan complete — {uploaded_file.name}", state="complete", expanded=False)

# ---------------------------------------------------------------------------
# Derived results (unchanged logic)
# ---------------------------------------------------------------------------

overall_score = round(sum(pillar_scores.values()) / len(pillar_scores))
csrd_score = framework_scores.get("ESRS / CSRD", 0)
risk_level = "Low"

high_gaps = 0 if gaps_df.empty else len(gaps_df[gaps_df["Severity"] == "High"])
if len(greenwashing_df) >= 4 or high_gaps >= 2:
    risk_level = "High"
elif len(greenwashing_df) >= 2 or high_gaps == 1:
    risk_level = "Medium"

strongest_pillar = max(pillar_scores, key=pillar_scores.get)
weakest_pillar = min(pillar_scores, key=pillar_scores.get)
gap_count = 0 if gaps_df.empty else len(gaps_df)
flag_count = 0 if greenwashing_df.empty else len(greenwashing_df)

summary = create_template_summary(
    overall_score, csrd_score, risk_level,
    strongest_pillar, weakest_pillar, gap_count, flag_count,
)
recommendations = build_recommendations(gaps_df, framework_scores, greenwashing_df)

# ---------------------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------------------

risk_class = {"Low": "deep", "Medium": "amber", "High": "red"}[risk_level]

col1, col2, col3, col4 = st.columns([1.35, 1, 1, 1])
with col1:
    st.markdown(
        '<div class="metric-card mint" style="display:flex; gap:18px; align-items:center;">'
        f'{ring_html(overall_score)}'
        '<div><div class="metric-label">ESG disclosure maturity</div>'
        f'<div class="metric-value deep">{maturity_band(overall_score)}</div>'
        f'<div class="metric-note">Grade {grade_from_score(overall_score)} · strongest area: {strongest_pillar}</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    metric_card(
        "CSRD / ESRS readiness",
        f'<div class="metric-value">{csrd_score}%</div>{bar_html(csrd_score)}',
        "Based on ESRS / CSRD disclosure evidence",
    )
with col3:
    metric_card(
        "Greenwashing risk",
        f'<div class="metric-value {risk_class}">{risk_level}</div>',
        f"{flag_count} claim flag(s) detected",
    )
with col4:
    metric_card(
        "Disclosure gaps",
        f'<div class="metric-value">{gap_count}</div>',
        f"{high_gaps} high severity · weakest area: {weakest_pillar}",
    )

st.write("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard",
    "Disclosure gaps",
    "Greenwashing review",
    "ESRS coverage",
    "Extracted text",
])

with tab1:
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel-title">ESG pillar strength</div>', unsafe_allow_html=True)
        st.plotly_chart(plot_radar(pillar_scores), use_container_width=True)
    with right:
        st.markdown('<div class="panel-title">Framework coverage</div>', unsafe_allow_html=True)
        st.plotly_chart(plot_frameworks(framework_scores), use_container_width=True)

    st.markdown(
        '<div class="exec-panel">'
        '<div class="panel-title">Executive summary</div>'
        f'<p>{summary}</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    recs_html = "".join(
        f'<div class="rec-item"><span class="rec-num">{i:02d}</span><span>{rec}</span></div>'
        for i, rec in enumerate(recommendations, start=1)
    )
    st.markdown(
        f'<div class="panel"><div class="panel-title">Recommended next actions</div>{recs_html}</div>',
        unsafe_allow_html=True,
    )

with tab2:
    st.markdown('<div class="panel-title">Disclosure gaps</div>', unsafe_allow_html=True)
    if gaps_df.empty:
        st.success("No major rule-based disclosure gaps detected.")
    else:
        st.dataframe(gaps_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download gap analysis CSV",
            gaps_df.to_csv(index=False).encode("utf-8"),
            file_name="esg_disclosure_gaps.csv",
            mime="text/csv",
        )

with tab3:
    st.markdown('<div class="panel-title">Greenwashing risk review</div>', unsafe_allow_html=True)
    if greenwashing_df.empty:
        st.success("No common greenwashing claims detected.")
    else:
        st.dataframe(greenwashing_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download greenwashing review CSV",
            greenwashing_df.to_csv(index=False).encode("utf-8"),
            file_name="greenwashing_risk_review.csv",
            mime="text/csv",
        )

with tab4:
    st.markdown('<div class="panel-title">ESRS topic coverage</div>', unsafe_allow_html=True)
    st.dataframe(esrs_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download ESRS coverage CSV",
        esrs_df.to_csv(index=False).encode("utf-8"),
        file_name="esrs_topic_coverage.csv",
        mime="text/csv",
    )

with tab5:
    st.markdown('<div class="panel-title">Extracted report text preview</div>', unsafe_allow_html=True)
    st.caption("Showing first 8,000 characters.")
    st.text_area("Extracted text", raw_text[:8000], height=420, label_visibility="collapsed")

st.markdown(
    '<div class="footer-note">Screening output — not an assurance opinion. '
    'Rule-based engine · processed in-session · no API required.</div>',
    unsafe_allow_html=True,
)
