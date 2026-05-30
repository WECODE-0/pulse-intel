import streamlit as st
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.database import get_connection, init_db
from scrapers.jobs_scraper import scrape_company_jobs
from scrapers.brand_scraper import scrape_brand_threats
from llm.gtm_analyzer import run_gtm_analysis
from llm.threat_analyzer import run_threat_analysis

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="PulseIntel",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg: #080C14;
    --surface: #0D1320;
    --surface2: #111827;
    --border: #1E293B;
    --accent: #3B82F6;
    --accent2: #06B6D4;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
    --text: #F1F5F9;
    --muted: #94A3B8;
    --mono: 'Space Mono', monospace;
    --sans: 'DM Sans', sans-serif;
}

* { font-family: var(--sans); }

.stApp {
    background: var(--bg);
    color: var(--text);
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem; max-width: 1400px; }

/* ── Input fix — placeholder and text color ── */
.stTextInput input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
    font-family: var(--mono) !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s;
}
.stTextInput input::placeholder {
    color: #64748B !important;
    opacity: 1 !important;
}
.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
.stTextInput label {
    color: #94A3B8 !important;
    font-size: 0.8rem !important;
    font-family: var(--mono) !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

/* ── Hero ── */
.hero {
    padding: 3rem 0 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.hero-badge {
    display: inline-block;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.3);
    color: var(--accent);
    font-family: var(--mono);
    font-size: 0.7rem;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.1em;
    margin-bottom: 1rem;
}
.hero-title {
    font-family: var(--mono);
    font-size: 3.5rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.02em;
    line-height: 1;
    margin: 0.5rem 0;
}
.hero-title span { color: var(--accent); }
.hero-subtitle {
    color: #94A3B8;
    font-size: 1rem;
    font-weight: 300;
    margin-top: 0.75rem;
    max-width: 600px;
    line-height: 1.6;
}
.hero-description {
    margin-top: 1.25rem;
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
}
.hero-pill {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
    color: #CBD5E1;
}
.hero-pill span { color: var(--accent); font-weight: 600; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #94A3B8;
    border-radius: 8px;
    font-family: var(--sans);
    font-size: 0.9rem;
    font-weight: 500;
    padding: 0.6rem 1.5rem;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 2rem; }

/* ── Buttons ── */
.stButton button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.2s !important;
    width: 100% !important;
}
.stButton button:hover {
    background: #2563EB !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(59,130,246,0.3) !important;
}

/* ── Metrics ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin: 1.5rem 0;
}
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
}
.metric-card.danger::before { background: var(--danger); }
.metric-card.warning::before { background: var(--warning); }
.metric-card.success::before { background: var(--success); }
.metric-label {
    font-family: var(--mono);
    font-size: 0.65rem;
    color: #64748B;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.metric-value {
    font-family: var(--mono);
    font-size: 2rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
}
.metric-value.danger { color: var(--danger); }
.metric-value.warning { color: var(--warning); }
.metric-value.success { color: var(--success); }

/* ── Brief Card ── */
.brief-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 2rem;
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
}
.brief-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: linear-gradient(180deg, var(--accent), var(--accent2));
}
.brief-signal {
    font-size: 1.1rem;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 1rem;
    line-height: 1.5;
}
.brief-intel {
    color: #94A3B8;
    font-size: 0.9rem;
    line-height: 1.7;
    margin-bottom: 1.5rem;
}
.brief-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
}
.brief-item-label {
    font-family: var(--mono);
    font-size: 0.65rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}
.brief-item-value {
    font-size: 0.85rem;
    color: #F1F5F9;
    font-weight: 500;
}
.confidence-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    font-family: var(--mono);
}
.confidence-high {
    background: rgba(16,185,129,0.15);
    color: var(--success);
    border: 1px solid rgba(16,185,129,0.3);
}
.confidence-medium {
    background: rgba(245,158,11,0.15);
    color: var(--warning);
    border: 1px solid rgba(245,158,11,0.3);
}
.confidence-low {
    background: rgba(239,68,68,0.15);
    color: var(--danger);
    border: 1px solid rgba(239,68,68,0.3);
}

/* ── Threat Cards ── */
.threat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1rem;
    align-items: start;
    transition: border-color 0.2s;
}
.threat-card:hover { border-color: #334155; }
.threat-card.critical { border-left: 3px solid var(--danger); }
.threat-card.high { border-left: 3px solid var(--warning); }
.threat-card.medium { border-left: 3px solid #A78BFA; }
.threat-card.low { border-left: 3px solid var(--success); }
.threat-score {
    font-family: var(--mono);
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1;
    min-width: 40px;
    text-align: center;
}
.threat-score.critical { color: var(--danger); }
.threat-score.high { color: var(--warning); }
.threat-score.medium { color: #A78BFA; }
.threat-score.low { color: var(--success); }
.threat-type-badge {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.65rem;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 0.4rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-phishing { background: rgba(239,68,68,0.15); color: var(--danger); }
.badge-credential_leak { background: rgba(245,158,11,0.15); color: var(--warning); }
.badge-lookalike_domain { background: rgba(167,139,250,0.15); color: #A78BFA; }
.badge-impersonation { background: rgba(6,182,212,0.15); color: var(--accent2); }
.badge-other { background: rgba(100,116,139,0.15); color: #94A3B8; }
.threat-summary {
    font-size: 0.875rem;
    color: #CBD5E1;
    line-height: 1.5;
}
.threat-url {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: #64748B;
    margin-top: 0.4rem;
    word-break: break-all;
}
.risk-level-pill {
    font-family: var(--mono);
    font-size: 0.65rem;
    padding: 4px 10px;
    border-radius: 20px;
    font-weight: 700;
    white-space: nowrap;
}
.pill-critical {
    background: rgba(239,68,68,0.15);
    color: var(--danger);
    border: 1px solid rgba(239,68,68,0.3);
}
.pill-high {
    background: rgba(245,158,11,0.15);
    color: var(--warning);
    border: 1px solid rgba(245,158,11,0.3);
}
.pill-medium {
    background: rgba(167,139,250,0.15);
    color: #A78BFA;
    border: 1px solid rgba(167,139,250,0.3);
}
.pill-low {
    background: rgba(16,185,129,0.15);
    color: var(--success);
    border: 1px solid rgba(16,185,129,0.3);
}

/* ── Section Headers ── */
.section-header {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin: 2rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Empty State ── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #64748B;
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; opacity: 0.4; }
.empty-text { font-family: var(--mono); font-size: 0.85rem; }

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: #F1F5F9 !important;
}

/* ── Footer ── */
.footer {
    margin-top: 4rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
    text-align: center;
    font-family: var(--mono);
    font-size: 0.7rem;
    color: #64748B;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)

# ── Helper Functions ─────────────────────────────────────────
def get_strategy_briefs(company: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM strategy_briefs
        WHERE company = ?
        ORDER BY created_at DESC
    """, (company,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_threat_alerts(brand: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM threat_alerts
        WHERE brand = ?
        ORDER BY risk_score DESC
    """, (brand,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_job_count(company: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM job_postings WHERE company = ?",
        (company,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_mention_count(brand: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM brand_mentions WHERE brand = ?",
        (brand,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def run_gtm(company: str):
    """Run full GTM pipeline."""
    with st.spinner(f"Scraping job postings for {company}..."):
        jobs = asyncio.run(scrape_company_jobs(company))
    st.success(f"✅ {len(jobs)} job postings scraped")
    with st.spinner("AI analyzing hiring signals..."):
        brief = run_gtm_analysis(company)
    if brief:
        st.success("✅ Strategy brief generated")
    else:
        st.warning("Analysis failed. Try again.")

def run_security(brand: str):
    """Run full security pipeline."""
    with st.spinner(f"Scanning open web for {brand} threats..."):
        mentions = asyncio.run(scrape_brand_threats(brand))
    st.success(f"✅ {len(mentions)} web mentions found")
    with st.spinner("AI analyzing threats and scoring risks..."):
        threats = run_threat_analysis(brand)
    if threats:
        st.success(f"✅ {len(threats)} threats identified")
    else:
        st.warning("No threats found.")

# ── Hero Header ──────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">⚡ WEB DATA UNLOCKED HACKATHON 2026</div>
    <div class="hero-title">Pulse<span>Intel</span></div>
    <div class="hero-subtitle">
        Enterprise web intelligence platform built for modern security
        and revenue teams. Monitor competitors. Detect threats. Act fast.
    </div>
    <div class="hero-description">
        <div class="hero-pill">📈 <span>GTM Intelligence</span> — Turn competitor hiring into strategy briefs</div>
        <div class="hero-pill">🛡️ <span>Security</span> — Detect phishing, leaks and impersonation in real time</div>
        <div class="hero-pill">⚡ <span>Bright Data</span> — Powered by real-time open web access</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "📈  GTM Intelligence",
    "🛡️  Security & Compliance"
])

# ════════════════════════════════════════════════════════════
# TAB 1 — GTM Intelligence
# ════════════════════════════════════════════════════════════
with tab1:

    col1, col2 = st.columns([4, 1])
    with col1:
        company_input = st.text_input(
            "TARGET COMPANY",
            placeholder="e.g. Stripe, OpenAI, Notion...",
            key="company_input"
        )
    with col2:
        st.write("")
        st.write("")
        analyze_clicked = st.button(
            "⚡ Analyze",
            key="run_gtm",
            use_container_width=True
        )

    # trigger on button click OR enter key
    if (analyze_clicked or company_input) and company_input:
        if analyze_clicked:
            run_gtm(company_input)

    # ── Metrics ──────────────────────────────────────────────
    if company_input:
        job_count = get_job_count(company_input)
        briefs = get_strategy_briefs(company_input)
        confidence = briefs[0].get("confidence", "—") if briefs else "—"

        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">Jobs Scraped</div>
                <div class="metric-value">{job_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Briefs Generated</div>
                <div class="metric-value">{len(briefs)}</div>
            </div>
            <div class="metric-card {'success' if confidence == 'High' else 'warning' if confidence == 'Medium' else ''}">
                <div class="metric-label">Confidence</div>
                <div class="metric-value {'success' if confidence == 'High' else 'warning' if confidence == 'Medium' else ''}">{confidence}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Data Source</div>
                <div class="metric-value" style="font-size:0.9rem;margin-top:6px;">Bright Data</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Strategy Briefs ───────────────────────────────────────
    if company_input:
        briefs = get_strategy_briefs(company_input)

        if briefs:
            st.markdown(
                '<div class="section-header">Strategy Briefs</div>',
                unsafe_allow_html=True
            )
            for brief in briefs:
                confidence = brief.get("confidence", "Low")
                conf_class = f"confidence-{confidence.lower()}"
                st.markdown(f"""
                <div class="brief-card">
                    <div class="brief-signal">📡 {brief.get('signal', '')}</div>
                    <div class="brief-intel">{brief.get('intel', '')}</div>
                    <div>
                        <span class="confidence-badge {conf_class}">
                            {confidence} Confidence
                        </span>
                    </div>
                    <div class="brief-grid">
                        <div>
                            <div class="brief-item-label">Timeline</div>
                            <div class="brief-item-value">{brief.get('expected_timeline', '—')}</div>
                        </div>
                        <div>
                            <div class="brief-item-label">Jobs Analyzed</div>
                            <div class="brief-item-value">{brief.get('jobs_analyzed', 0)}</div>
                        </div>
                        <div>
                            <div class="brief-item-label">Generated</div>
                            <div class="brief-item-value">{str(brief.get('created_at', ''))[:10]}</div>
                        </div>
                    </div>
                    <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #1E293B;">
                        <div class="brief-item-label">Threat To Competitors</div>
                        <div class="brief-item-value" style="margin-top:0.4rem;color:#94A3B8;font-size:0.85rem;line-height:1.6;">
                            {brief.get('threat_to_competitors', '—')}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-text">Enter a company name and click Analyze</div>
            </div>
            """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# TAB 2 — Security & Compliance
# ════════════════════════════════════════════════════════════
with tab2:

    col1, col2 = st.columns([4, 1])
    with col1:
        brand_input = st.text_input(
            "TARGET BRAND",
            placeholder="e.g. PayPal, Google, Microsoft...",
            key="brand_input"
        )
    with col2:
        st.write("")
        st.write("")
        scan_clicked = st.button(
            "🔍 Scan",
            key="run_security",
            use_container_width=True
        )

    # trigger on button click OR enter key
    if (scan_clicked or brand_input) and brand_input:
        if scan_clicked:
            run_security(brand_input)

    # ── Metrics ──────────────────────────────────────────────
    if brand_input:
        mention_count = get_mention_count(brand_input)
        threats = get_threat_alerts(brand_input)

        critical = len([t for t in threats if t.get("risk_level") == "CRITICAL"])
        high = len([t for t in threats if t.get("risk_level") == "HIGH"])
        medium = len([t for t in threats if t.get("risk_level") == "MEDIUM"])
        low = len([t for t in threats if t.get("risk_level") == "LOW"])

        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">Mentions Scanned</div>
                <div class="metric-value">{mention_count}</div>
            </div>
            <div class="metric-card danger">
                <div class="metric-label">Critical</div>
                <div class="metric-value danger">{critical}</div>
            </div>
            <div class="metric-card warning">
                <div class="metric-label">High</div>
                <div class="metric-value warning">{high}</div>
            </div>
            <div class="metric-card success">
                <div class="metric-label">Medium / Low</div>
                <div class="metric-value">{medium + low}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Threat Alerts ─────────────────────────────────────────
    if brand_input:
        threats = get_threat_alerts(brand_input)

        if threats:
            st.markdown(
                '<div class="section-header">Threat Alerts</div>',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns([2, 4])
            with col1:
                filter_level = st.selectbox(
                    "FILTER BY RISK",
                    ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    key="filter_level"
                )

            filtered = threats if filter_level == "All" else [
                t for t in threats if t.get("risk_level") == filter_level
            ]

            st.markdown(
                f'<p style="color:#64748B;font-family:monospace;font-size:0.8rem;">'
                f'Showing {len(filtered)} threats</p>',
                unsafe_allow_html=True
            )

            for threat in filtered:
                risk = threat.get("risk_level", "LOW").lower()
                score = threat.get("risk_score", 0)
                threat_type = threat.get("threat_type", "other").lower().replace(" ", "_")
                url = threat.get("source_url", "")
                summary = threat.get("summary", "")

                st.markdown(f"""
                <div class="threat-card {risk}">
                    <div class="threat-score {risk}">{score}</div>
                    <div>
                        <span class="threat-type-badge badge-{threat_type}">
                            {threat_type.replace('_', ' ')}
                        </span>
                        <div class="threat-summary">{summary}</div>
                        <div class="threat-url">🔗 {url[:90]}{'...' if len(url) > 90 else ''}</div>
                    </div>
                    <span class="risk-level-pill pill-{risk}">{risk.upper()}</span>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">🛡️</div>
                <div class="empty-text">Enter a brand name and click Scan</div>
            </div>
            """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    ⚡ PULSEINTEL — WEB DATA UNLOCKED HACKATHON 2026
    &nbsp;·&nbsp; POWERED BY BRIGHT DATA + GROQ
    &nbsp;·&nbsp; BUILT WITH ❤️ BY WECODERS
</div>
""", unsafe_allow_html=True)