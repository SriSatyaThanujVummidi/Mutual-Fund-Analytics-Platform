import requests
import pandas as pd
import os

def fetch_nav(scheme_code):
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        meta = data['meta']
        nav_records = data['data']  # list of {date, nav}
        
        df = pd.DataFrame(nav_records)
        df['scheme_code'] = scheme_code
        df['scheme_name'] = meta.get('scheme_name', '')
        df['fund_house']  = meta.get('fund_house', '')
        
        print(f"✅ Fetched {len(df)} NAV records for: {meta.get('scheme_name')}")
        return df
    else:
        print(f"❌ Failed to fetch scheme {scheme_code} — Status: {response.status_code}")
        return None

# Fetch for HDFC Top 100 Direct
df_hdfc = fetch_nav(125497)

if df_hdfc is not None:
    save_path = "data/raw/live_hdfc_top100_nav.csv"
    df_hdfc.to_csv(save_path, index=False)
    print(f"💾 Saved to {save_path}")
    print(df_hdfc.head())

# 5 schemes to fetch
schemes = {
    119551: "SBI_Bluechip",
    120503: "ICICI_Bluechip",
    118632: "Nippon_LargeCap",
    119092: "Axis_Bluechip",
    120841: "Kotak_Bluechip",
}

all_dfs = []

for code, name in schemes.items():
    df = fetch_nav(code)
    if df is not None:
        save_path = f"data/raw/live_{name}_nav.csv"
        df.to_csv(save_path, index=False)
        all_dfs.append(df)

# Combine all into one file
combined = pd.concat(all_dfs, ignore_index=True)
combined.to_csv("data/raw/live_all5_nav_combined.csv", index=False)
print(f"\n📊 Total live NAV records fetched: {len(combined)}")