import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Any

from helpers import (
    fetch_expiring_soon,
    fetch_natjecaji,
    fetch_scraping_logs,
    fetch_statistics,
    format_iznos,
    generate_ai_summary,
    load_css,
    parse_rok,
    render_template,
    safe_text,
    search_natjecaji,
    trigger_scraping,
)

# Page config
st.set_page_config(
    page_title="FIDIT AI Assistant",
    layout="wide",
    initial_sidebar_state="collapsed"
)

load_css()


# ==================== MAIN APP ====================

def main():
    st.markdown(
        render_template(
            "header.html",
            {
                "title": "FIDIT AI Assistant",
                "subtitle": "Jednostavan pregled javnih natječaja uz AI podršku.",
            },
        ),
        unsafe_allow_html=True,
    )

    stats = fetch_statistics()
    nav_col, info_col = st.columns([3.2, 1.8])
    with nav_col:
        st.markdown('<div class="top-nav-wrap">', unsafe_allow_html=True)
        page = st.radio(
            "Navigacija",
            ["Početna", "Pretraživanje", "Statistika", "Administracija"],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with info_col:
        if stats:
            st.markdown(
                '<div class="top-nav-stats">'
                f"Ukupno: {stats.get('total_natjecaji', 0)} | "
                f"Aktivni: {stats.get('active_natjecaji', 0)} | "
                f"Ističu uskoro: {stats.get('expiring_soon', 0)}"
                '</div>',
                unsafe_allow_html=True,
            )

    with st.expander("EU AI Act obavijest", expanded=False):
        st.markdown(render_template("ai_notice.html"), unsafe_allow_html=True)

    if page == "Početna":
        show_homepage(stats)
    elif page == "Pretraživanje":
        show_search_page()
    elif page == "Statistika":
        show_statistics_page(stats)
    elif page == "Administracija":
        show_admin_page()


def show_homepage(stats):
    """Show homepage with overview."""
    st.subheader("Pregled")

    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Ukupno natječaja", value=stats.get("total_natjecaji", 0))
        with col2:
            st.metric(label="Aktivni", value=stats.get("active_natjecaji", 0))
        with col3:
            st.metric(label="Ističu uskoro", value=stats.get("expiring_soon", 0))
        with col4:
            st.metric(label="Izdavatelji", value=stats.get("total_izdavatelji", 0))

    st.markdown("---")

    st.subheader("Natječaji koji uskoro istječu")
    expiring = fetch_expiring_soon(30)

    if expiring:
        for nat in expiring[:6]:
            rok = parse_rok(nat.get("rok_prijave"))
            days_left = "N/A"
            rok_str = "N/A"
            if rok:
                days_left = f"{max((rok - datetime.now(rok.tzinfo)).days, 0)} dana"
                rok_str = rok.strftime('%d.%m.%Y')

            url = nat.get("url") or "#"
            st.markdown(
                render_template(
                    "home_expiring_card.html",
                    {
                        "naziv": safe_text(nat.get("naziv", "Bez naziva")),
                        "kategorija": safe_text(nat.get("kategorija", "N/A")),
                        "podrucje": safe_text(nat.get("podrucje_istrazivanja", "N/A")),
                        "iznos": safe_text(format_iznos(nat.get("iznos_financiranja"))),
                        "rok": safe_text(rok_str),
                        "days_left": safe_text(days_left),
                        "url": safe_text(url),
                    },
                ),
                unsafe_allow_html=True,
            )
    else:
        st.info("Nema natječaja koji uskoro istječu.")


def show_search_page():
    """Show search and filtering page."""
    st.subheader("Pretraživanje natječaja")

    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "search_page" not in st.session_state:
        st.session_state.search_page = 0
    if "ai_summaries" not in st.session_state:
        st.session_state.ai_summaries = {}

    with st.form("search_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            search_term = st.text_input("Ključna riječ", placeholder="npr. inovacije, AI, istraživanje")
        with col2:
            kategorija = st.selectbox(
                "Kategorija",
                ["Sve", "Znanstveno istraživanje", "Inovacije", "Potpora poduzetništvu"],
            )
        with col3:
            podrucje = st.selectbox(
                "Područje",
                ["Sve", "ICT", "Medicina", "Društvene znanosti", "Multidisciplinarno"],
            )

        submitted = st.form_submit_button("Pretraži", type="primary")

    if submitted:
        kat = None if kategorija == "Sve" else kategorija
        pod = None if podrucje == "Sve" else podrucje
        st.session_state.search_results = search_natjecaji(
            search_term=search_term if search_term else None,
            kategorija=kat,
            podrucje=pod,
        )
        st.session_state.search_page = 0  # reset to first page on new search

    results = st.session_state.search_results
    if results:
        PAGE_SIZE = 10
        total = len(results)
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = st.session_state.search_page

        st.markdown("---")

        # Header row: title left, page info right
        hcol, pcol = st.columns([3, 1])
        with hcol:
            st.subheader(f"Rezultati ({total})")
        with pcol:
            st.markdown(
                f'<div style="text-align:right;padding-top:0.6rem;font-size:0.9rem;opacity:0.8">'  
                f'Stranica {page + 1} / {total_pages}</div>',
                unsafe_allow_html=True,
            )

        # Render current page items
        page_items = results[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
        for nat in page_items:
            natjecaj_id = nat.get("id")
            opis = nat.get('opis') or "Bez opisa"
            short_opis = opis[:220] + ("..." if len(opis) > 220 else "")
            rok = parse_rok(nat.get("rok_prijave"))
            url = nat.get("url") or "#"
            st.markdown(
                render_template(
                    "search_result_card.html",
                    {
                        "naziv": safe_text(nat.get("naziv", "Bez naziva")),
                        "kategorija": safe_text(nat.get("kategorija", "N/A")),
                        "podrucje": safe_text(nat.get("podrucje_istrazivanja", "N/A")),
                        "opis": safe_text(short_opis),
                        "iznos": safe_text(format_iznos(nat.get("iznos_financiranja"))),
                        "rok": safe_text(rok.strftime('%d.%m.%Y') if rok else 'N/A'),
                        "url": safe_text(url),
                    },
                ),
                unsafe_allow_html=True,
            )

            if natjecaj_id is not None:
                action_col, info_col = st.columns([1.1, 3.9])
                with action_col:
                    if st.button("Generiraj AI sažetak", key=f"ai_summary_{natjecaj_id}", use_container_width=True):
                        with st.spinner("Generiram AI sažetak..."):
                            summary_response = generate_ai_summary(int(natjecaj_id))
                        if summary_response and isinstance(summary_response.get("summary"), dict):
                            st.session_state.ai_summaries[natjecaj_id] = summary_response
                        else:
                            st.error("AI sažetak nije moguće generirati.")

                with info_col:
                    cached_summary = st.session_state.ai_summaries.get(natjecaj_id)
                    if cached_summary and isinstance(cached_summary.get("summary"), dict):
                        summary = cached_summary["summary"]
                        disclaimer = cached_summary.get(
                            "disclaimer",
                            "AI-generirani sadržaj - provjerite službenu dokumentaciju",
                        )
                        st.markdown(
                            "<div class='ai-summary-card'>"
                            "<div class='ai-summary-title'>AI sažetak</div>"
                            f"<div class='ai-summary-text'>{safe_text(summary.get('sazetek', 'N/A'))}</div>"
                            f"<div class='ai-summary-meta'><strong>Ključne riječi:</strong> {safe_text(summary.get('kljucne_rijeci', 'N/A'))}</div>"
                            f"<div class='ai-summary-meta'><strong>Relevantnost:</strong> {safe_text(summary.get('preporuka_relevantnosti', 'N/A'))}</div>"
                            f"<div class='ai-summary-disclaimer'>{safe_text(disclaimer)}</div>"
                            "</div>",
                            unsafe_allow_html=True,
                        )

            st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)

        # Pagination controls
        if total_pages > 1:
            st.markdown("")
            nav_cols = st.columns([1, 1, 4, 1, 1])
            with nav_cols[0]:
                if st.button("⟨⟨", disabled=page == 0, use_container_width=True, key="pg_first"):
                    st.session_state.search_page = 0
                    st.rerun()
            with nav_cols[1]:
                if st.button("⟨", disabled=page == 0, use_container_width=True, key="pg_prev"):
                    st.session_state.search_page = page - 1
                    st.rerun()
            with nav_cols[2]:
                # Clickable page number buttons (show up to 7 around current)
                half = 3
                start_p = max(0, min(page - half, total_pages - 2 * half - 1))
                end_p = min(total_pages, start_p + 2 * half + 1)
                btn_cols = st.columns(end_p - start_p)
                for i, p_idx in enumerate(range(start_p, end_p)):
                    label = f"**{p_idx + 1}**" if p_idx == page else str(p_idx + 1)
                    if btn_cols[i].button(label, key=f"pg_{p_idx}", use_container_width=True):
                        st.session_state.search_page = p_idx
                        st.rerun()
            with nav_cols[3]:
                if st.button("⟩", disabled=page >= total_pages - 1, use_container_width=True, key="pg_next"):
                    st.session_state.search_page = page + 1
                    st.rerun()
            with nav_cols[4]:
                if st.button("⟩⟩", disabled=page >= total_pages - 1, use_container_width=True, key="pg_last"):
                    st.session_state.search_page = total_pages - 1
                    st.rerun()

    elif submitted:
        st.info("Nema rezultata za zadane kriterije.")


def show_statistics_page(stats):
    """Show statistics and visualizations."""
    st.subheader("Statistika")

    natjecaji = fetch_natjecaji()

    if not natjecaji:
        st.warning("Nema podataka za prikaz statistike.")
        return

    df = pd.DataFrame(natjecaji)

    if stats:
        a, b, c = st.columns(3)
        a.metric("Ukupno", stats.get("total_natjecaji", 0))
        b.metric("Aktivni", stats.get("active_natjecaji", 0))
        c.metric("Ističu uskoro", stats.get("expiring_soon", 0))

    st.markdown("---")

    st.subheader("Distribucija po kategorijama")
    if 'kategorija' in df.columns:
        kat_counts = df['kategorija'].value_counts()
        fig = px.pie(
            values=kat_counts.values,
            names=kat_counts.index,
            hole=0.45,
        )
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Po područjima istraživanja")
        if 'podrucje_istrazivanja' in df.columns:
            pod_counts = df['podrucje_istrazivanja'].value_counts()
            fig = px.bar(
                x=pod_counts.index,
                y=pod_counts.values,
                labels={'x': 'Područje', 'y': 'Broj natječaja'},
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Raspodjela financiranja")
        if 'iznos_financiranja' in df.columns:
            df_filtered = df[df['iznos_financiranja'].notna()]
            if not df_filtered.empty:
                fig = px.histogram(
                    df_filtered,
                    x='iznos_financiranja',
                    nbins=20,
                    labels={'iznos_financiranja': 'Iznos (EUR)'},
                )
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rokovi natječaja")
    if 'rok_prijave' in df.columns:
        df_timeline = df[df['rok_prijave'].notna()].copy()
        if not df_timeline.empty:
            df_timeline['rok_prijave'] = pd.to_datetime(df_timeline['rok_prijave'])
            df_timeline = df_timeline.sort_values('rok_prijave')

            fig = px.scatter(
                df_timeline,
                x='rok_prijave',
                y='naziv',
                size='iznos_financiranja' if 'iznos_financiranja' in df.columns else None,
                hover_data=['kategorija', 'podrucje_istrazivanja'],
                labels={'rok_prijave': 'Rok prijave', 'naziv': 'Natječaj'},
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)


def show_admin_page():
    """Show administration page."""
    st.subheader("Administracija")

    st.markdown("### Web scraping")
    st.write("Ručno pokrenite prikupljanje podataka s definiranih izvora.")

    if st.button("Pokreni scraping", type="primary"):
        with st.spinner("Prikupljanje podataka u tijeku..."):
            success = trigger_scraping()

            if success:
                st.success("Scraping uspješno završen.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Greška pri scrapingu. Provjerite API server.")

    st.markdown("---")

    st.markdown("### Povijest scrapinga")
    logs = fetch_scraping_logs(limit=10)
    if logs is not None:
        if logs:
            df_logs = pd.DataFrame(logs)

            source_root_links = {
                "HAMAG-BICRO": "https://hamagbicro.hr",
                "HRZZ": "https://hrzz.hr",
                "CORDIS": "https://cordis.europa.eu",
                "MINGO": "https://mingo.gov.hr",
            }

            if "izvor" in df_logs.columns:
                df_logs["izvor_root_link"] = df_logs["izvor"].map(source_root_links)
                if "url" in df_logs.columns:
                    df_logs["izvor_root_link"] = df_logs["url"].fillna(df_logs["izvor_root_link"])
                df_logs = df_logs.drop(columns=["izvor"], errors="ignore")

                preferred_order = [
                    "izvor_root_link",
                    "status",
                    "natjecaji_pronadeni",
                    "natjecaji_dodani",
                    "natjecaji_azurirani",
                    "execution_time",
                    "created_at",
                    "error_message",
                    "id",
                ]
                existing_order = [col for col in preferred_order if col in df_logs.columns]
                remaining_cols = [col for col in df_logs.columns if col not in existing_order]
                df_logs = df_logs[existing_order + remaining_cols]

            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("Nema zapisa o scrapingu.")
    else:
        st.error("Greška pri dohvaćanju logova.")


# ==================== RUN APP ====================

if __name__ == "__main__":
    main()
