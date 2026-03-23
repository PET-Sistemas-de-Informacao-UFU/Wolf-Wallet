"""
🐺 Wolf Wallet — Mobile Responsive CSS

Injects global CSS media queries for mobile devices.
Called once in app.py to improve UX on small screens.

Usage:
    from components.mobile_css import inject_mobile_css
    inject_mobile_css()
"""

from __future__ import annotations

import streamlit as st


def inject_mobile_css() -> None:
    """Injeta CSS responsivo global para melhor experiência mobile."""
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


_MOBILE_CSS: str = """
<style>
/* =============================================
   🐺 Wolf Wallet — Mobile Responsive Overrides
   ============================================= */

/* ---- Viewport & base ---- */
@media (max-width: 768px) {

    /* Reduce overall padding */
    .main .block-container {
        padding: 1rem 0.8rem !important;
        max-width: 100% !important;
    }

    /* Sidebar compacto */
    [data-testid="stSidebar"] .block-container {
        padding: 0.5rem 0.8rem !important;
    }
    [data-testid="stSidebar"] h3 {
        font-size: 1.1rem !important;
    }

    /* Títulos menores */
    h1 {
        font-size: 1.5rem !important;
        line-height: 1.3 !important;
    }
    h2 {
        font-size: 1.25rem !important;
    }

    /* Cards do dashboard — empilha em 2x2 */
    .wolf-card {
        padding: 0.8rem 1rem !important;
        margin-bottom: 0.4rem !important;
    }
    .wolf-card-value {
        font-size: 1.2rem !important;
    }
    .wolf-card-title {
        font-size: 0.78rem !important;
    }
    .wolf-card-icon {
        font-size: 1.3rem !important;
    }

    /* Colunas do Streamlit — permite wrap */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.3rem !important;
    }

    /* NÃO empilhar colunas por padrão.
       Só empilha os metric cards (4 colunas do dashboard/extrato). */
    [data-testid="stMetric"] {
        min-width: 0 !important;
    }

    /* Tabelas — scroll horizontal */
    [data-testid="stDataFrame"],
    .stDataFrame {
        overflow-x: auto !important;
    }

    /* Metric cards menores */
    [data-testid="stMetric"] {
        padding: 0.4rem !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1rem !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }

    /* Botões — touch-friendly */
    .stButton > button {
        min-height: 44px !important;
        font-size: 0.9rem !important;
    }

    /* Expanders — toque fácil */
    [data-testid="stExpander"] summary {
        min-height: 44px !important;
        padding: 0.5rem !important;
    }

    /* Radio buttons — mais espaço entre opções */
    [data-testid="stRadio"] label {
        padding: 0.35rem 0 !important;
    }

    /* Filtros — forçar stack vertical */
    [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* Plotly charts — altura mínima */
    .js-plotly-plot {
        min-height: 250px !important;
    }

    /* Dividers — menos margem */
    hr {
        margin: 0.5rem 0 !important;
    }

    /* Caption e texto auxiliar */
    .stCaption, .stMarkdown p {
        font-size: 0.85rem !important;
    }

    /* Feed de atividades — font menor */
    [data-testid="stMarkdown"] div[style*="display: flex"] {
        font-size: 0.82rem !important;
        padding: 0.3rem 0.5rem !important;
    }

    /* Rendimentos cards internos */
    div[style*="border-left: 4px solid"] {
        padding: 0.8rem 1rem !important;
    }
    div[style*="border-left: 4px solid"] p[style*="font-size: 1.5rem"] {
        font-size: 1.15rem !important;
    }
    div[style*="border-left: 4px solid"] p[style*="font-size: 0.85rem"] {
        font-size: 0.75rem !important;
    }
}

/* ---- Telas muito pequenas (< 480px) — full stack ---- */
@media (max-width: 480px) {

    .main .block-container {
        padding: 0.5rem 0.5rem !important;
    }

    h1 {
        font-size: 1.3rem !important;
    }

    .wolf-card-value {
        font-size: 1.05rem !important;
    }

    /* Login centralizado */
    [data-testid="stForm"] {
        padding: 0 !important;
    }
}

/* ---- Melhoria geral (todas as telas) ---- */

/* Scrollbar sutil */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.15);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255,255,255,0.25);
}

/* Transições suaves em interações */
.stButton > button,
[data-testid="stExpander"] summary,
.wolf-card {
    transition: all 0.2s ease !important;
}

</style>
"""
