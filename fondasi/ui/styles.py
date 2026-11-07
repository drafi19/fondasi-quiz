"""One calm, professional stylesheet for the internal tool."""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
:root {
  --paper: #FAF9F6;
  --ink: #1A1A1A;
  --muted: #5F5B54;
  --line: #E4E1DA;
  --accent: #0F5B55;
  --panel: #FFFFFF;
}

.stApp {
  background-color: var(--paper);
  color: var(--ink);
}

html, body, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.block-container {
  max-width: 880px;
  padding-top: 2.5rem;
  padding-bottom: 4rem;
}

#MainMenu, footer, header[data-testid="stHeader"] {
  visibility: hidden;
}

h1, h2, h3, h4 {
  font-family: Georgia, "Times New Roman", serif;
  color: var(--ink);
  font-weight: 600;
  letter-spacing: -0.01em;
}

h1 { font-size: 2.25rem; margin-bottom: 0.25rem; }
h2 { font-size: 1.5rem; margin-top: 1.5rem; }
h3 { font-size: 1.15rem; }

p, li, label, .stMarkdown, .stCaption {
  color: var(--ink);
  line-height: 1.55;
}

.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--muted);
}

a { color: var(--accent); }

.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  border-bottom: 1px solid var(--line);
}

.stTabs [data-baseweb="tab"] {
  color: var(--muted);
  padding: 0.6rem 0.9rem;
}

.stTabs [aria-selected="true"] {
  color: var(--accent);
  border-bottom: 2px solid var(--accent);
}

.stTextInput input, .stTextArea textarea, .stNumberInput input {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--ink);
}

.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: var(--accent);
  box-shadow: none;
}

.stButton > button, .stDownloadButton > button {
  background: var(--accent);
  color: #FFFFFF;
  border: 1px solid var(--accent);
  border-radius: 8px;
  font-weight: 600;
  padding: 0.45rem 1rem;
}

.stButton > button:hover, .stDownloadButton > button:hover {
  background: #0B4742;
  border-color: #0B4742;
  color: #FFFFFF;
}

div[data-testid="stExpander"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
}

div[data-testid="stExpander"] details summary {
  color: var(--ink);
  font-weight: 600;
}

div[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.9rem 1rem;
}

div[data-testid="stAlert"] {
  border-radius: 12px;
  border: 1px solid var(--line);
}

hr { border-color: var(--line); }

.fondasi-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem 1.15rem;
  margin-bottom: 0.75rem;
}

.fondasi-meta {
  color: var(--muted);
  font-size: 0.9rem;
}

.fondasi-quote {
  border-left: 3px solid var(--accent);
  padding-left: 0.75rem;
  color: var(--muted);
  font-style: italic;
}

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

/* The engine picker renders in a portal outside .stApp, so it inherited a
   background without a matching text colour. Force both. */
div[data-testid="stDialog"] > div {
  background: #FFFFFF;
  border: 1px solid #E4E1DA;
}
div[data-testid="stDialog"] h1,
div[data-testid="stDialog"] h2,
div[data-testid="stDialog"] h3,
div[data-testid="stDialog"] p,
div[data-testid="stDialog"] div,
div[data-testid="stDialog"] span,
div[data-testid="stDialog"] label,
div[data-testid="stDialog"] li {
  color: #1A1A1A;
}
</style>
"""


def apply_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
