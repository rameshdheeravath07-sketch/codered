import pandas as pd
import requests
import io

def build_dynamic_dhan_universe():
    """
    Downloads the official Dhan Scrip Master and the NSE Top 500,
    and dynamically maps the Symbols to Dhan Security IDs.
    """
    print("🧠 Building Dynamic Dhan Universe...")
    try:
        # 1. Fetch the Official Dhan Master CSV
        dhan_url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        dhan_df = pd.read_csv(dhan_url)
        
        # Filter only for NSE Equities (Ignore options, futures, and BSE for the screener)
        dhan_df = dhan_df[(dhan_df['SEM_EXM_EXCH_ID'] == 'NSE') & (dhan_df['SEM_SERIES'] == 'EQ')]
        
        # Create a mapping dictionary: {'TATASTEEL': '3499'}
        # Dhan's CSV uses 'SEM_CUSTOM_SYMBOL' for the ticker and 'SEM_SMST_SECURITY_ID' for the ID
        dhan_map = dict(zip(dhan_df['SEM_CUSTOM_SYMBOL'], dhan_df['SEM_SMST_SECURITY_ID'].astype(str)))

        # 2. Fetch the Live Nifty 500 List from NSE
        nse_url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        nse_res = requests.get(nse_url, headers=headers, timeout=10)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        
        # 3. Merge them! Take the top 200 stocks and get their Dhan IDs
        dynamic_universe = {}
        for symbol in nse_df['Symbol'].tolist()[:200]: # Scanning top 200 for speed
            if symbol in dhan_map:
                dynamic_universe[symbol] = dhan_map[symbol]
                
        print(f"✅ Successfully mapped {len(dynamic_universe)} dynamic Security IDs.")
        return dynamic_universe

    except Exception as e:
        print(f"⚠️ Dynamic Mapping Failed: {e}")
        # Emergency Fallback
        return {"TATASTEEL": "3499", "HDFCBANK": "1333", "RELIANCE": "2885"}

# Initialize the dynamic universe!
DHAN_UNIVERSE = build_dynamic_dhan_universe()