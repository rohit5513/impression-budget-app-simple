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
has_country = "country" in base.columns

if has_country:
    base["country"] = base["country"].astype(str)

    country_vals = base["country"].dropna().unique().tolist()
    all_labels = {"all", "all/overall", "overall"}

    # All actual country labels except the ones that mean "all"
    other_countries = [c for c in country_vals if c.strip().lower() not in all_labels]

    options = ["Overall"] + sorted(other_countries)
    country = st.selectbox("Country", options)
else:
    st.caption("No country column found in this export; using all markets together.")

# --- Overall CPM (ALL/Overall) ---
overall_cost = base["cost"].sum()
overall_impr = base["impressions"].sum()
overall_cpm = (overall_cost / overall_impr) * 1000 if overall_impr > 0 else np.nan

THRESHOLD_IMPR = 100_000  # minimum impressions to trust a country CPM
used_country_cpm = False  # flag for the note
country_impr = 0

# --- Decide which CPM to use: country (if enough data) or overall ---
if has_country and country != "ALL/Overall":
    seg_country = base[base["country"] == country].copy()
    country_impr = seg_country["impressions"].sum()
    country_cost = seg_country["cost"].sum()

    if country_impr >= THRESHOLD_IMPR:
        # Enough data → use country CPM
        cpm_eff = (country_cost / country_impr) * 1000
        used_country_cpm = True
    else:
        # Not enough (or zero) → fall back to overall CPM
        cpm_eff = overall_cpm
        used_country_cpm = False
else:
    # ALL/Overall or no country column → use overall CPM
    cpm_eff = overall_cpm
    used_country_cpm = False

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
    if has_country and country != "ALL/Overall":
        if used_country_cpm:
            st.caption(
                f"Country used: {country} (≥ {THRESHOLD_IMPR:,} impressions for this Platform × Campaign type)."
            )
        else:
            st.caption(
                f"Note: {country} does not have enough impressions for this Platform × Campaign type, "
                f"so CPM and budget are based on the overall (ALL/Overall) data."
            )

    st.markdown("---")

# --- Important notes in simple language ---
with st.expander("Important notes (please read)"):
    st.markdown(
        """
- **How the calculator works**  
  - It uses your past data to work out an average **CPM** (cost per 1,000 impressions).  
  - **Budget = (Target impressions ÷ 1000) × CPM (EUR).**

- **How country is used**  
  - If you pick a country (NL, BE, Benelux, etc.) **and** that country has at least **100,000 impressions** in the history for that Platform × Campaign type, the calculator uses that country’s own CPM.  
  - If the country has **too little or no data**, the tool automatically falls back to the **overall CPM (Overall)** so you still get a stable estimate. A short note under the result tells you what happened.

- **Time factor (delivery over days)**  
  - You won’t get all impressions immediately. They are spread over the **flight length (days)** you enter.  
  - The app shows your **daily budget** and **daily estimated impressions**.

- **Things this tool does NOT control**  
  - This is a **planning guide**, not exact truth.  
  - Real results still depend on:
    - **Ad quality / Quality Score**  
    - **Keywords** and match types  
    - **Where ads show** (apps vs websites)  
    - **Who you target** and competition  
  - Our data is limited to what’s in the export, so treat the number as an **estimate**, not a promise.  
  - It’s smart to keep a **15–20% buffer** for normal changes in price, competition, and pacing.
        """
    )
