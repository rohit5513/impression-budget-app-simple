
# 🎯 Impression Budget Calculator (Minimal, Repo-Data Only)

This Streamlit app **does not accept uploads**. It reads a fixed data file from the repo and shows a minimal UI:
- Select **Platform**
- Select **Campaign type**
- Enter **Target impressions**
- Output: **Estimated budget (EUR)** (and nothing else)

## Data Source (from repo)
Place a CSV at `data/campaigns.csv` in the repo with these columns (case/spacing agnostic):
- `Campaign status`
- `Platform`
- `Campaign type`
- `Cost` (EUR)
- `Impression` or `Impressions` (integer)

The app normalizes headers (lowercases, strips spaces) and treats any variant of "impression(s)".  
It automatically filters to `Campaign status = Enabled` and rows with positive Cost/Impressions.

## How it calculates
- Effective CPM for the selected segment = `(ΣCost / ΣImpressions) * 1000`
- Estimated Budget (EUR) = `(Target Impressions / 1000) × Effective CPM`

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to Streamlit Community Cloud
1. Push this folder to a **public GitHub repo**.
2. On https://streamlit.io/cloud → **New app** → select your repo.
3. Set **Main file path** to `streamlit_app.py` and deploy.

## Replace the sample data
Swap `data/campaigns.csv` with your full export. Keep the column names mentioned above.
