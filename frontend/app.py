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

    results = st.session_state.search_results
    if results:
        st.markdown("---")
        st.subheader(f"Rezultati ({len(results)})")
        for nat in results:
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
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("Nema zapisa o scrapingu.")
    else:
        st.error("Greška pri dohvaćanju logova.")


# ==================== RUN APP ====================

if __name__ == "__main__":
    main()
