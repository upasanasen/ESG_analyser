import re
import fitz
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="ESG Report Analyser",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #071313 0%, #0b1720 50%, #081411 100%);
    color: #f8fafc;
}
section[data-testid="stSidebar"] {
    background: #0b1220;
    border-right: 1px solid rgba(148, 163, 184, 0.18);
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
.hero {
    padding: 30px;
    border-radius: 24px;
    background: radial-gradient(circle at top right, rgba(16,185,129,.28), transparent 32%),
                linear-gradient(135deg, rgba(15,23,42,.98), rgba(8,47,73,.8));
    border: 1px solid rgba(148, 163, 184, 0.2);
    box-shadow: 0 24px 80px rgba(0,0,0,.28);
    margin-bottom: 22px;
}
.hero h1 {
    font-size: 42px;
    line-height: 1.05;
    margin: 0 0 10px 0;
    color: #f8fafc;
}
.hero p {
    color: #cbd5e1;
    font-size: 16px;
    margin: 0;
    max-width: 900px;
}
.tag {
    display:inline-block;
    margin: 16px 8px 0 0;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(16,185,129,.12);
    border: 1px solid rgba(16,185,129,.28);
    color: #a7f3d0;
    font-size: 12px;
    font-weight: 600;
}
.metric-card {
    padding: 22px;
    border-radius: 20px;
    background: rgba(15, 23, 42, 0.82);
    border: 1px solid rgba(148, 163, 184, 0.18);
    box-shadow: 0 14px 40px rgba(0,0,0,.22);
    min-height: 135px;
}
.metric-label { color: #94a3b8; font-size: 13px; margin-bottom: 8px; }
.metric-value { color: #34d399; font-size: 34px; font-weight: 800; line-height: 1; }
.metric-note { color: #cbd5e1; font-size: 12px; margin-top: 10px; }
.panel {
    padding: 20px;
    border-radius: 20px;
    background: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.18);
    box-shadow: 0 14px 40px rgba(0,0,0,.2);
    margin-bottom: 18px;
}
.panel-title {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 10px;
}
.small-muted { color: #cbd5e1; font-size: 14px; line-height: 1.7; }
</style>
""", unsafe_allow_html=True)

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

def plot_radar(pillar_scores):
    categories = list(pillar_scores.keys())
    values = list(pillar_scores.values())

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name="Score"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        height=390,
        margin=dict(l=40, r=40, t=30, b=30),
    )
    return fig

def plot_frameworks(framework_scores):
    df = pd.DataFrame({
        "Framework": list(framework_scores.keys()),
        "Coverage": list(framework_scores.values())
    })
    fig = px.bar(df, x="Framework", y="Coverage", text="Coverage", range_y=[0, 100])
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        height=390,
        margin=dict(l=20, r=20, t=30, b=30),
    )
    return fig

def kpi_card(label: str, value: str, note: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.markdown("## 🌿 ESG Report Analyser")
    st.caption("Public no-API version")
    st.divider()
    st.markdown("### Screening modules")
    st.markdown("""
    - ESG pillar maturity
    - CSRD / ESRS readiness
    - GRI, TCFD, GHG Protocol coverage
    - Greenwashing risk flags
    - Disclosure gaps
    - Template-based executive summary
    """)
    st.divider()
    st.info("This public version uses a rule-based ESG intelligence engine. No API key, quota, or billing needed.")

st.markdown(
    """
    <div class="hero">
        <h1>ESG Report Analyser</h1>
        <p>Upload a sustainability report and get a no-API ESG screening dashboard covering CSRD readiness, framework coverage, disclosure gaps, greenwashing risks, and recommended next actions.</p>
        <span class="tag">CSRD / ESRS</span>
        <span class="tag">GRI</span>
        <span class="tag">TCFD</span>
        <span class="tag">GHG Protocol</span>
        <span class="tag">Greenwashing Risk</span>
        <span class="tag">No API Required</span>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a sustainability report PDF",
    type=["pdf"],
    help="Upload a text-based PDF. Scanned/image-based PDFs may not extract correctly."
)

if uploaded_file is None:
    col1, col2, col3 = st.columns(3)
    with col1:
        kpi_card("Step 1", "Upload", "Add a sustainability or ESG report PDF.")
    with col2:
        kpi_card("Step 2", "Scan", "The app checks ESG, CSRD, GRI, TCFD, and GHG terms.")
    with col3:
        kpi_card("Step 3", "Improve", "Use the dashboard to identify reporting gaps.")
    st.stop()

try:
    raw_text = extract_pdf_text(uploaded_file)
except Exception as exc:
    st.error(f"Could not read the PDF: {exc}")
    st.stop()

if len(raw_text.strip()) < 300:
    st.error("The report text could not be extracted properly. This may be a scanned/image-based PDF. Try a text-based PDF.")
    st.stop()

text = clean_text(raw_text)

framework_scores, pillar_scores = calculate_scores(text)
gaps_df = build_gap_table(text)
greenwashing_df = detect_greenwashing(text)
esrs_df = esrs_coverage(text)

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
summary = create_template_summary(
    overall_score,
    csrd_score,
    risk_level,
    strongest_pillar,
    weakest_pillar,
    0 if gaps_df.empty else len(gaps_df),
    0 if greenwashing_df.empty else len(greenwashing_df)
)
recommendations = build_recommendations(gaps_df, framework_scores, greenwashing_df)

st.success(f"Analysed: {uploaded_file.name}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    kpi_card("Overall ESG Score", f"{overall_score}/100", f"Grade {grade_from_score(overall_score)}")
with col2:
    kpi_card("CSRD Readiness", f"{csrd_score}%", "Based on ESRS / CSRD disclosure evidence")
with col3:
    kpi_card("Greenwashing Risk", risk_level, f"{0 if greenwashing_df.empty else len(greenwashing_df)} claim flag(s)")
with col4:
    kpi_card("Frameworks Checked", "5", "GRI, ESRS, TCFD, GHG, SDGs")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "⚠️ Disclosure gaps",
    "🧪 Greenwashing review",
    "🗂 ESRS coverage",
    "📄 Extracted text"
])

with tab1:
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel"><div class="panel-title">ESG Pillar Strength</div>', unsafe_allow_html=True)
        st.plotly_chart(plot_radar(pillar_scores), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="panel-title">Framework Coverage</div>', unsafe_allow_html=True)
        st.plotly_chart(plot_frameworks(framework_scores), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel"><div class="panel-title">Template-Based Executive Summary</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="small-muted">{summary}</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel"><div class="panel-title">Recommended Next Actions</div>', unsafe_allow_html=True)
    for i, rec in enumerate(recommendations, start=1):
        st.markdown(f"**{i}.** {rec}")
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("Disclosure Gaps")
    if gaps_df.empty:
        st.success("No major rule-based disclosure gaps detected.")
    else:
        st.dataframe(gaps_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download gap analysis CSV",
            gaps_df.to_csv(index=False).encode("utf-8"),
            file_name="esg_disclosure_gaps.csv",
            mime="text/csv"
        )

with tab3:
    st.subheader("Greenwashing Risk Review")
    if greenwashing_df.empty:
        st.success("No common greenwashing claims detected.")
    else:
        st.dataframe(greenwashing_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download greenwashing review CSV",
            greenwashing_df.to_csv(index=False).encode("utf-8"),
            file_name="greenwashing_risk_review.csv",
            mime="text/csv"
        )

with tab4:
    st.subheader("ESRS Topic Coverage")
    st.dataframe(esrs_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download ESRS coverage CSV",
        esrs_df.to_csv(index=False).encode("utf-8"),
        file_name="esrs_topic_coverage.csv",
        mime="text/csv"
    )

with tab5:
    st.subheader("Extracted Report Text Preview")
    st.caption("Showing first 8,000 characters.")
    st.text_area("Extracted text", raw_text[:8000], height=420)
