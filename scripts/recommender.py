import pandas as pd

def recommend_funds(risk_appetite: str, top_n: int = 3) -> pd.DataFrame:
    """Recommend top N funds based on investor risk appetite."""
    perf  = pd.read_csv('../data/processed/clean_performance.csv')
    funds = pd.read_csv('../data/raw/01_fund_master.csv')

    risk_map = {
        'Low'      : ['Low', 'Moderately Low'],
        'Moderate' : ['Moderate', 'Moderately High'],
        'High'     : ['High', 'Very High']
    }
    allowed_grades = risk_map.get(risk_appetite.title(), ['Moderate'])
    merged = perf.merge(funds[['amfi_code','scheme_name','risk_category',
                                'fund_house','category','expense_ratio_pct']],
                        on='amfi_code', how='left')
    filtered = merged[merged['risk_category'].isin(allowed_grades)]
    filtered = filtered.sort_values('sharpe_ratio', ascending=False)
    cols = ['scheme_name','fund_house','risk_category',
            'sharpe_ratio','return_3yr_pct','expense_ratio_pct']
    return filtered[cols].head(top_n).reset_index(drop=True)

if __name__ == "__main__":
    for a in ['Low', 'Moderate', 'High']:
        print(f"\n=== {a} Risk ===")
        print(recommend_funds(a).to_string(index=False))
