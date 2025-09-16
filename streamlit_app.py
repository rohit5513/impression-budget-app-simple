
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Impression Budget Calculator", layout="centered")

# --- Load data from repo (no upload) ---
# Expect a CSV at data/campaigns.csv in the repo
DATA_PATH = "data/campaigns.csv"

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize headers (case/spacing)
    df.columns = [c.strip().lower() for c in df.columns]
    # Handle impression column variants (e.g., " impression " with spaces)
    rename_map = {}
    for c in list(df.columns):
        if c.replace(" ", "") in {"impressions", "impression"}:
            rename_map[c] = "impressions"
    if rename_map:
        df = df.rename(columns=rename_map)

    # Required columns
    req = ["campaign status","platform","campaign type","cost","impressions"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")

    # Clean
    df = df[(df["impressions"] > 0) & (df["cost"] > 0)].copy()

    # Hard rule: only Enabled rows (as per requirement to keep UI minimal)
    #df = df[df["campaign status"].str.lower() == "enabled"]

    # Precompute effective CPM per row for reference (not shown)
    df["cpm_calc"] = (df["cost"] / df["impressions"]) * 1000

    return df

try:
    df = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

st.title("Ads. Impression Budget Calculator")

# --- Inputs (exactly as requested) ---
platforms = sorted(df["platform"].dropna().unique().tolist())
platform = st.selectbox("Platform", platforms)

ctype_opts = sorted(df[df["platform"] == platform]["campaign type"].dropna().unique().tolist())
ctype = st.selectbox("Campaign type", ctype_opts)

target_impr = st.number_input("Target impressions", min_value=1_000, step=50_000, value=5_000_000, help=None)

# --- Compute effective CPM for selected segment ---
seg = df[(df["platform"] == platform) & (df["campaign type"] == ctype)].copy()

if seg.empty:
    st.warning("No data for the selected Platform × Campaign type.")
else:
    # Effective CPM = (Σcost / Σimpressions) * 1000
    cost_sum = seg["cost"].sum()
    impr_sum = seg["impressions"].sum()
    cpm_eff = (cost_sum / impr_sum) * 1000 if impr_sum > 0 else np.nan

    # Estimated budget in EUR (ONLY output to show)
    if np.isnan(cpm_eff):
        st.warning("Unable to compute CPM for this segment.")
    else:
        estimated_budget = (target_impr / 1000.0) * cpm_eff
        st.metric("Estimated budget (EUR)", f"{estimated_budget:,.2f}")
