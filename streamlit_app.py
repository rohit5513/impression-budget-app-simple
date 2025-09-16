
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Impression Budget Calculator", layout="centered")

# --- Resolve data path robustly (relative to this file OR working dir) ---
APP_DIR = Path(__file__).parent.resolve()
CANDIDATES = [
    APP_DIR / "data" / "campaigns.csv",   # repo/app folder /data/campaigns.csv
    APP_DIR / "campaigns.csv",            # repo/app folder /campaigns.csv
    Path.cwd() / "data" / "campaigns.csv",# working dir /data/campaigns.csv
    Path.cwd() / "campaigns.csv",         # working dir /campaigns.csv
]

DATA_PATH = None
for p in CANDIDATES:
    if p.exists() and p.is_file():
        DATA_PATH = p
        break

if DATA_PATH is None:
    st.error("Could not find `campaigns.csv`. Make sure it exists at `data/campaigns.csv` next to `streamlit_app.py` or at the repo root.")
    st.caption("Checked locations:")
    for p in CANDIDATES:
        st.text(str(p))
    st.stop()

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    # Standardize impressions column variants
    rename_map = {}
    for c in list(df.columns):
        if c.replace(" ", "") in {"impression", "impressions"}:
            rename_map[c] = "impressions"
    if rename_map:
        df = df.rename(columns=rename_map)

    req = ["campaign status","platform","campaign type","cost","impressions"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path.name}: {missing}")

    # Clean + keep Enabled only
    df = df[(df["impressions"] > 0) & (df["cost"] > 0)].copy()
    df = df[df["campaign status"].str.lower() == "enabled"]
    df["cpm_calc"] = (df["cost"] / df["impressions"]) * 1000
    return df

try:
    df = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Error loading data from {DATA_PATH} — {e}")
    st.stop()

st.title("🎯 Impression Budget Calculator")

# --- Inputs ---
platforms = sorted(df["platform"].dropna().unique().tolist())
platform = st.selectbox("Platform", platforms)

ctype_opts = sorted(df[df["platform"] == platform]["campaign type"].dropna().unique().tolist())
ctype = st.selectbox("Campaign type", ctype_opts)

target_impr = st.number_input("Target impressions", min_value=1_000, step=50_000, value=5_000_000)

# --- Compute effective CPM & budget ---
seg = df[(df["platform"] == platform) & (df["campaign type"] == ctype)]
if seg.empty:
    st.warning("No data for the selected Platform × Campaign type.")
else:
    cost_sum = seg["cost"].sum()
    impr_sum = seg["impressions"].sum()
    cpm_eff = (cost_sum / impr_sum) * 1000 if impr_sum > 0 else np.nan
    if np.isnan(cpm_eff):
        st.warning("Unable to compute CPM for this segment.")
    else:
        estimated_budget = (target_impr / 1000.0) * cpm_eff
        st.metric("Estimated budget (EUR)", f"{estimated_budget:,.2f}")
