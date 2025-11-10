import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Impression Budget Calculator", layout="centered")

# --- Load data from repo (no upload) ---
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

    # Ensure numeric types (handles numbers as strings)
    if "cost" in df.columns:
        df["cost"] = pd.to_numeric(df["cost"].astype(str).str.replace(",", ""), errors="coerce")
    if "impressions" in df.columns:
        df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce")

    # Required columns
    req = ["campaign status", "platform", "campaign type", "cost", "impressions"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")

    # Clean: keep rows with positive cost & impressions (keep ALL statuses)
    df = df[(df["impressions"] > 0) & (df["cost"] > 0)].copy()

    # Effective CPM per row (for reference if needed)
    df["cpm_calc"] = (df["cost"] / df["impressions"]) * 1000

    return df

try:
    df = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

st.title("Ads. Impression Budget Calculator")

# --- Inputs ---
platforms = sorted(df["platform"].dropna().unique().tolist())
platform = st.selectbox("Platform", platforms)

ctype_opts = sorted(df[df["platform"] == platform]["campaign type"].dropna().unique().tolist())
ctype = st.selectbox("Campaign type", ctype_opts)

target_impr = st.number_input(
    "Target impressions",
    min_value=1_000,
    step=1_000,
    value=5_000_000
)

# --- Base slice for selected Platform × Campaign type ---
base = df[(df["platform"] == platform) & (df["campaign type"] == ctype)].copy()

if base.empty:
    st.warning("No data for the selected Platform × Campaign type.")
    st.stop()

# --- Country selection (if column exists) ---
country = "ALL/Overall"
if "country" in base.columns:
    base["country"] = base["country"].astype(str)

    country_vals = base["country"].dropna().unique().tolist()
    all_labels = {"all", "all/overall", "overall"}

    # All actual country labels except the ones that mean "all"
    other_countries = [c for c in country_vals if c.strip().lower() not in all_labels]

    # Show selector: ALL/Overall + individual countries
    options = ["ALL/Overall"] + sorted(other_countries)
    country = st.selectbox("Country", options)
else:
    st.caption("No country column found in this export; using all markets together.")

# --- Build segment based on country choice ---
if "country" in base.columns and country != "ALL/Overall":
    seg = base[base["country"] == country].copy()
else:
    seg = base.copy()  # ALL/Overall

if seg.empty:
    st.warning("No data for the selected Platform × Campaign type (and Country).")
    st.stop()

# --- Compute CPMs: overall and (optional) country ---
overall_cost = base["cost"].sum()
overall_impr = base["impressions"].sum()
overall_cpm = (overall_cost / overall_impr) * 1000 if overall_impr > 0 else np.nan

cost_sum = seg["cost"].sum()
impr_sum = seg["impressions"].sum()

THRESHOLD_IMPR = 100_000  # minimum impressions to trust a country-specific CPM
used_overall = False

if "country" in base.columns and country != "ALL/Overall":
    # If the country has enough impressions, use its own CPM
    if impr_sum >= THRESHOLD_IMPR:
        cpm_eff = (cost_sum / impr_sum) * 1000 if impr_sum > 0 else np.nan
        used_overall = False
    else:
        # Fallback: not enough history for that country, use overall CPM
        cpm_eff = overall_cpm
        used_overall = True
else:
    # If no country chosen / ALL/Overall, just use overall CPM
    cpm_eff = overall_cpm

# --- Estimated budget + time factor ---
if np.isnan(cpm_eff):
    st.warning("Unable to compute CPM for this selection.")
else:
    estimated_budget = (target_impr / 1000.0) * cpm_eff
    st.metric("Estimated budget (EUR)", f"€ {estimated_budget:,.2f}")

    # Time factor / pacing
    flight_days = st.number_input("Flight length (days)", min_value=1, value=14, step=1)
    st.metric("Daily budget (EUR)", f"€ {(estimated_budget / flight_days):,.2f}")
    st.metric("Daily impressions (est.)", f"{(target_impr / flight_days):,.0f}")

    # Country note
    if "country" in base.columns and country != "ALL/Overall":
        if used_overall:
            st.caption(
                f"Note: {country} has less than {THRESHOLD_IMPR:,} impressions in history, "
                "so CPM falls back to the overall (ALL/Overall) value."
            )
        else:
            st.caption(
                f"Country used: {country} (≥ {THRESHOLD_IMPR:,} impressions for this Platform × Campaign type)."
            )

    st.markdown("---")

# --- Important notes in simple language ---
with st.expander("Important notes (please read)"):
    st.markdown(
        """
- **What this tool does:**  
  - It uses your past data to work out an average **CPM** (cost per 1,000 impressions).  
  - **Budget = (Target impressions ÷ 1000) × CPM (EUR).**

- **How country is used:**  
  - If you pick a country (NL, BE, Benelux, etc.) **and** that country has at least **100,000 impressions** in history,  
    the calculator uses that country’s own CPM.  
  - If the country has **less than 100,000 impressions**, it is **not stable enough**, so the calculator falls back to the  
    **overall CPM (ALL/Overall)** instead of showing a shaky number.  
  - A short note below the result tells you whether the tool used **country CPM** or **overall CPM**.

- **Time factor (delivery over days):**  
  - You won’t get all impressions immediately. They are spread over the **flight length (days)** you enter.  
  - The app shows you the **daily budget** and **daily estimated impressions** to make this clear.

- **Limitations to keep in mind:**  
  - This is a **planning guide**, not the exact truth.  
  - Real results depend on **ad quality/Quality Score**, **keywords**, **where ads show (apps vs websites)**, and **who you target**.  
  - Our data is limited to what’s in the export, so treat the number as an **estimate** rather than a guarantee.  
  - It’s smart to keep a **15–20% buffer** to cover normal changes in price, competition, and pacing.
        """
    )
