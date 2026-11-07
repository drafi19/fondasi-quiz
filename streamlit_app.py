from __future__ import annotations

import streamlit as st

from fondasi.runtime_env import mirror_secrets
from fondasi.ui.pages import render_build, render_review, render_take
from fondasi.ui.styles import apply_styles

st.set_page_config(
    page_title="Fondasi",
    page_icon="F",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# On Streamlit Community Cloud the key lives in st.secrets, not in the process
# environment. Copy it across before any provider is built.
try:
    mirror_secrets(st.secrets)
except Exception:
    pass

apply_styles()

st.title("Fondasi")
st.caption(
    "A source-grounded quiz generator. Every item must point to a verbatim quote "
    "from the source you provide."
)

build_tab, review_tab, take_tab = st.tabs(["Build", "Review", "Take"])
with build_tab:
    render_build()
with review_tab:
    render_review()
with take_tab:
    render_take()
