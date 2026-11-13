"""
JobHunter SN — Dashboard Streamlit
Lance : streamlit run app/main.py --server.port 8501
"""

import os
import requests
import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API = f"{BACKEND_URL}/api/v1"

st.set_page_config(
    page_title="JobHunter SN",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS PERSONNALISÉ (dark premium)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Layout ───────────────────────────────────────────── */
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"]          { background: #161b22; border-right: 1px solid #30363d; }
[data-testid="stHeader"]           { background: transparent; }
.block-container                   { padding-top: 1.5rem; }

/* ── Stat card ────────────────────────────────────────── */
.stat-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 16px 20px;
  text-align: center;
}
.stat-value { font-size: 2rem; font-weight: 700; color: #e6edf3; }
.stat-label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }

/* ── Job card ─────────────────────────────────────────── */
.job-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 14px;
  transition: border-color .15s;
}
.job-card:hover { border-color: #58a6ff; }
.job-title  { font-size: 1.05rem; font-weight: 600; color: #e6edf3; margin-bottom: 4px; }
.job-company{ font-size: 0.9rem; color: #8b949e; }
.job-meta   { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }

/* ── Score badge ──────────────────────────────────────── */
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge-high   { background: #0f4a3a; color: #3fb950; border: 1px solid #238636; }
.badge-medium { background: #3a2d0f; color: #d29922; border: 1px solid #9e6a03; }
.badge-low    { background: #2d1b1b; color: #f85149; border: 1px solid #6e3630; }
.badge-grey   { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
.badge-type   { background: #1a2e4a; color: #58a6ff; border: 1px solid #1f4a8a; }
.badge-remote { background: #1a3a2e; color: #3fb950; border: 1px solid #238636; }
.badge-source { background: #21262d; color: #79c0ff; border: 1px solid #30363d; }

/* ── Skill tags ───────────────────────────────────────── */
.skill-tag {
  display: inline-block;
  background: #1a2e4a;
  color: #79c0ff;
  border: 1px solid #1f4a8a;
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 0.72rem;
  margin: 2px;
}
.skill-miss {
  background: #2d1b1b;
  color: #f85149;
  border-color: #6e3630;
}

/* ── Explanation ──────────────────────────────────────── */
.explanation {
  font-size: 0.82rem;
  color: #8b949e;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #30363d;
}

/* ── Section header ───────────────────────────────────── */
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #30363d;
}
.section-title { font-size: 1.15rem; font-weight: 600; color: #e6edf3; }
.section-count { font-size: 0.85rem; color: #8b949e; }

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
  background: #21262d !important;
  border: 1px solid #30363d !important;
  color: #c9d1d9 !important;
  border-radius: 8px !important;
}
.stButton > button:hover {
  border-color: #58a6ff !important;
  color: #58a6ff !important;
}
.stProgress > div > div { background: #238636; }

/* ── Sidebar elements ─────────────────────────────────── */
.sidebar-label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FONCTIONS API
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def fetch_jobs(params: dict) -> dict:
    try:
        resp = requests.get(f"{API}/jobs/", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"total": 0, "jobs": [], "page": 1, "per_page": 20, "has_more": False}


@st.cache_data(ttl=300)
def fetch_stats() -> list:
    try:
        resp = requests.get(f"{API}/jobs/stats", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def trigger_scrape(source=None):
    try:
        resp = requests.post(f"{API}/scrape/", json={"source": source}, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSANTS UI
# ─────────────────────────────────────────────────────────────────────────────

def score_badge(score: float) -> str:
    pct = int(score * 100)
    if score >= 0.75:
        return f'<span class="badge badge-high">✓ {pct}%</span>'
    elif score >= 0.50:
        return f'<span class="badge badge-medium">◈ {pct}%</span>'
    elif score >= 0.30:
        return f'<span class="badge badge-low">◉ {pct}%</span>'
    else:
        return f'<span class="badge badge-grey">{pct}%</span>'


def job_card(job: dict):
    title    = job.get("title", "—")
    company  = job.get("company") or "Entreprise non précisée"
    location = job.get("location") or "Dakar"
    source   = job.get("source", "")
    score    = job.get("matching_score", 0.0)
    jtype    = job.get("job_type")
    remote   = job.get("is_remote", False)
    url      = job.get("url", "#")
    matched  = job.get("skills_matched", [])[:8]
    missing  = job.get("skills_missing", [])[:4]
    expl     = job.get("match_explanation", "")
    scraped  = job.get("scraped_at", "")

    # Date relative
    date_str = ""
    if scraped:
        try:
            dt = datetime.fromisoformat(scraped.replace("Z", ""))
            delta = datetime.utcnow() - dt
            if delta.days == 0:
                date_str = "Aujourd'hui"
            elif delta.days == 1:
                date_str = "Hier"
            else:
                date_str = f"il y a {delta.days}j"
        except Exception:
            pass

    # Skills HTML
    skill_html = ""
    for s in matched:
        skill_html += f'<span class="skill-tag">{s}</span>'
    for s in missing:
        skill_html += f'<span class="skill-tag skill-miss">↑ {s}</span>'

    # Badges
    badges = score_badge(score)
    badges += f' <span class="badge badge-source">{source}</span>'
    if jtype:
        badges += f' <span class="badge badge-type">{jtype.upper()}</span>'
    if remote:
        badges += ' <span class="badge badge-remote">🌐 Remote</span>'
    if date_str:
        badges += f' <span class="badge badge-grey">{date_str}</span>'

    expl_html = f'<div class="explanation">{expl}</div>' if expl else ""

    html = f"""
    <div class="job-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
        <div>
          <div class="job-title"><a href="{url}" target="_blank" style="color:#e6edf3;text-decoration:none">{title}</a></div>
          <div class="job-company">🏢 {company} &nbsp;•&nbsp; 📍 {location}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:1.6rem;font-weight:700;color:{'#3fb950' if score>=0.75 else '#d29922' if score>=0.5 else '#8b949e'}">{int(score*100)}%</div>
          <div style="font-size:0.72rem;color:#8b949e">match</div>
        </div>
      </div>
      <div class="job-meta">{badges}</div>
      <div style="margin-top:10px">{skill_html}</div>
      {expl_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def stat_card(value, label, color="#58a6ff"):
    st.markdown(f"""
    <div class="stat-card">
      <div class="stat-value" style="color:{color}">{value}</div>
      <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## 🎯 JobHunter SN")
        st.markdown(
            '<div style="font-size:.8rem;color:#8b949e;margin-bottom:1rem">'
            'Offres IT filtrées pour <strong style="color:#e6edf3">Ibrahima FALL</strong>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Scraping ──────────────────────────────────────────────────────────
        st.markdown("**⚙️ Scraping**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Tout scraper", use_container_width=True):
                with st.spinner("Lancement..."):
                    result = trigger_scrape()
                st.success(result.get("message", "Lancé !"))
                st.cache_data.clear()
        with col2:
            if st.button("🧹 Actualiser", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        st.divider()

        # ── Filtres ───────────────────────────────────────────────────────────
        st.markdown("**🔍 Filtres**")

        min_score = st.slider(
            "Score minimum", 0, 100, 40, 5,
            format="%d%%", help="Filtre les offres par score de compatibilité"
        ) / 100

        source = st.selectbox(
            "Source",
            ["Toutes", "emploi_dakar", "senjob", "novojob", "google_jobs"],
        )

        job_type = st.selectbox(
            "Type de contrat",
            ["Tous", "stage", "pfe", "cdi", "cdd", "alternance"],
        )

        remote_only = st.checkbox("Remote uniquement")

        search = st.text_input("🔎 Recherche", placeholder="Titre, entreprise...")

        sort_by = st.radio(
            "Trier par",
            ["Score", "Date"],
            horizontal=True,
        )

        st.divider()

        # ── Profil actif ──────────────────────────────────────────────────────
        st.markdown("**👤 Profil actif**")
        st.markdown(
            '<div style="font-size:.8rem;color:#8b949e">'
            '📚 Master 2 SRT — ESP/UCAD<br>'
            '🔧 Réseaux • Cyber • Cloud • Data<br>'
            '📍 Dakar + Remote'
            '</div>',
            unsafe_allow_html=True,
        )

    return {
        "min_score": min_score,
        "source": None if source == "Toutes" else source,
        "job_type": None if job_type == "Tous" else job_type,
        "is_remote": True if remote_only else None,
        "search": search or None,
        "sort_by": "matching_score" if sort_by == "Score" else "scraped_at",
    }


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    filters = render_sidebar()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<h1 style='color:#e6edf3;font-size:1.8rem;margin-bottom:0'>🎯 JobHunter SN</h1>"
        "<p style='color:#8b949e;margin-top:2px'>Offres IT • Dakar & Sénégal • Personnalisées pour votre profil</p>",
        unsafe_allow_html=True,
    )

    # ── Stats cards ───────────────────────────────────────────────────────────
    stats = fetch_stats()
    total_jobs = sum(s.get("total", 0) for s in stats)
    high_match = sum(s.get("high_match", 0) for s in stats)
    medium_match = sum(s.get("medium_match", 0) for s in stats)
    n_sources = len(stats)

    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card(total_jobs, "Offres totales", "#58a6ff")
    with c2: stat_card(high_match, "Match excellent (≥75%)", "#3fb950")
    with c3: stat_card(medium_match, "Match correct (50–75%)", "#d29922")
    with c4: stat_card(n_sources, "Sources actives", "#bc8cff")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Barre de score par source ─────────────────────────────────────────────
    if stats:
        with st.expander("📊 Détail par source", expanded=False):
            cols = st.columns(len(stats))
            for i, s in enumerate(stats):
                with cols[i]:
                    avg = s.get("avg_score", 0)
                    st.markdown(
                        f"<div style='text-align:center'>"
                        f"<div style='font-size:.8rem;color:#8b949e'>{s['source']}</div>"
                        f"<div style='font-size:1.3rem;font-weight:700;color:#58a6ff'>{s['total']}</div>"
                        f"<div style='font-size:.75rem;color:#8b949e'>moy {int(avg*100)}%</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.progress(avg)

    # ── Pagination state ──────────────────────────────────────────────────────
    if "page" not in st.session_state:
        st.session_state.page = 1

    # ── Appel API ─────────────────────────────────────────────────────────────
    params = {
        "min_score": filters["min_score"],
        "sort_by": filters["sort_by"],
        "page": st.session_state.page,
        "per_page": 15,
    }
    if filters["source"]:      params["source"] = filters["source"]
    if filters["job_type"]:    params["job_type"] = filters["job_type"]
    if filters["is_remote"]:   params["is_remote"] = True
    if filters["search"]:      params["search"] = filters["search"]

    with st.spinner("Chargement des offres..."):
        data = fetch_jobs(params)

    total  = data.get("total", 0)
    jobs   = data.get("jobs", [])
    has_more = data.get("has_more", False)

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-title">Offres d\'emploi</span>'
        f'<span class="section-count">{total} résultats • Page {st.session_state.page}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not jobs:
        st.info("Aucune offre trouvée. Lancez un scraping ou ajustez les filtres.")
        st.markdown(
            "_💡 Si c'est le premier lancement, cliquez sur **🔄 Tout scraper** dans la barre latérale._"
        )
        return

    # ── Cartes d'offres ───────────────────────────────────────────────────────
    for job in jobs:
        job_card(job)

    # ── Pagination ────────────────────────────────────────────────────────────
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.session_state.page > 1:
            if st.button("← Précédent", use_container_width=True):
                st.session_state.page -= 1
                st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center;color:#8b949e;font-size:.85rem;padding-top:8px'>"
            f"Page {st.session_state.page}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if has_more:
            if st.button("Suivant →", use_container_width=True):
                st.session_state.page += 1
                st.rerun()


if __name__ == "__main__":
    main()
