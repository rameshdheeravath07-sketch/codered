from dhanhq import dhanhq
import pandas as pd
from datetime import datetime, timedelta
import time
import requests
import io
from ai_core import calculate_advanced_signals

# --- USE LOWERCASE AS PER YOUR RECENT SNIPPET ---
client_id = "2604202082"
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc2OTU1MzQ3LCJpYXQiOjE3NzY4Njg5NDcsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmHealthyVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTEwNTY5OTkwIn0.zzsRiicO523mz9nwMUiR3BQi-_WwMY0unHPkuoTZ7DmKiEcQzXS8T5B-cOMc23f2O9GM8WxAIfv86K9SqOccEA"

dhan = dhanhq(client_id=client_id, access_token=access_token)

def build_dynamic_dhan_universe():
    try:
        dhan_df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv")
        dhan_df = dhan_df[(dhan_df['SEM_EXM_EXCH_ID'] == 'NSE') & (dhan_df['SEM_SERIES'] == 'EQ')]
        dhan_map = dict(zip(dhan_df['SEM_CUSTOM_SYMBOL'], dhan_df['SEM_SMST_SECURITY_ID'].astype(str)))
        res = requests.get("https://archives.nseindia.com/content/indices/ind_nifty500list.csv", headers={'User-Agent': 'Mozilla/5.0'})
        nse_df = pd.read_csv(io.StringIO(res.text))
        # Scanning top 30 for speed (Test with 30 first, then increase)
        return {s: dhan_map[s] for s in nse_df['Symbol'].tolist()[:30] if s in dhan_map}
    except: return {"TATASTEEL": "3499"}

DHAN_UNIVERSE = build_dynamic_dhan_universe()

def fetch_historical_candles(security_id):
    """Fetches 1-min data. Covers weekends and after-hours."""
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        # Use historical_minute_data for better after-hours results
        req = dhan.historical_minute_data(security_id, 'NSE_EQ', 'EQUITY', from_date, to_date)
        if req and req.get('status') == 'success' and req.get('data'):
            df = pd.DataFrame(req['data'])
            df.columns = [c.capitalize() for c in df.columns]
            return df.dropna().reset_index(drop=True)
        return pd.DataFrame()
    except: return pd.DataFrame()

def run_master_scanner():
    print(f"🚀 STARTING GLOBAL SCAN...")
    stock_results = []
    
    for name, sec_id in DHAN_UNIVERSE.items():
        time.sleep(1.0) # 🛡️ SECURE 1-SECOND THROTTLE (Prevents Rate Limit 100%)
        
        df = fetch_historical_candles(sec_id)
        if df.empty or len(df) < 50:
            print(f"❌ {name}: No Data")
            continue

        try:
            val = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-20])
            chg = ((val - prev) / prev) * 100
            
            # Smart Money Calcs
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            vwap = (tp * df['Volume']).sum() / df['Volume'].sum()
            vol_surge = float(df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1])
            
            prob, target, surge = calculate_advanced_signals(df)

            stock_results.append({
                "name": name, "ltp": val, "chg": chg, "vol_surge": vol_surge, "ai_prob": prob, "ai_target": target,
                "gainers": chg > 0.3, "losers": chg < -0.3,
                "vol_break_up": vol_surge > 2.5 and chg > 0,
                "vol_break_down": vol_surge > 2.5 and chg < 0,
                "bb_break": val > df['Close'].rolling(20).mean().iloc[-1] + (df['Close'].rolling(20).std().iloc[-1]*2),
                "high_5d": val >= df['High'].max() * 0.99,
                "low_5d": val <= df['Low'].min() * 1.01,
                "buy_5m": (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and (vol_surge > 2.0),
                "break_15m": val > df['Close'].iloc[-15:-1].max(),
                "break_1h": val > df['Close'].iloc[-60:-1].max(),
                "smart_money": (val > vwap) and (vol_surge > 3.0)
            })
            print(f"✅ {name}: Scanned (Prob: {int(prob)}%)")
        except: continue

    # --- FINAL FORMATTING ---
    def f(l): return [{"name": x["name"], "ltp": f"₹{x['ltp']:,.2f}", "chg": f"{x['chg']:+.2f}%", "raw_chg": x['chg']} for x in l]
    def fa(l): return [{"name": x["name"], "ltp": f"{int(x['ai_prob'])}% Prob", "chg": f"Tgt: ₹{x['ai_target']:,.0f}", "raw_chg": x['chg']} for x in l]

    return {
        "gainers": f(sorted([r for r in stock_results if r["gainers"]], key=lambda x: x["chg"], reverse=True)[:5]),
        "losers": f(sorted([r for r in stock_results if r["losers"]], key=lambda x: x["chg"])[:5]),
        "vol_break_up": f(sorted([r for r in stock_results if r["vol_break_up"]], key=lambda x: x["vol_surge"], reverse=True)[:5]),
        "vol_break_down": f(sorted([r for r in stock_results if r["vol_break_down"]], key=lambda x: x["vol_surge"], reverse=True)[:5]),
        "vol_gainers": f(sorted(stock_results, key=lambda x: x["vol_surge"], reverse=True)[:5]),
        "bb_break": f(sorted([r for r in stock_results if r["bb_break"]], key=lambda x: x["chg"], reverse=True)[:5]),
        "high_5d": f(sorted([r for r in stock_results if r["high_5d"]], key=lambda x: x["chg"], reverse=True)[:5]),
        "low_5d": f(sorted([r for r in stock_results if r["low_5d"]], key=lambda x: x["chg"])[:5]),
        "buy_5m": f(sorted([r for r in stock_results if r["buy_5m"]], key=lambda x: x["chg"], reverse=True)[:5]),
        "break_15m": f(sorted([r for r in stock_results if r["break_15m"]], key=lambda x: x["chg"], reverse=True)[:5]),
        "break_1h": f(sorted([r for r in stock_results if r["break_1h"]], key=lambda x: x["chg"], reverse=True)[:5]),
        "ai_alpha": fa(sorted([r for r in stock_results if r["smart_money"] or r["ai_prob"] > 70], key=lambda x: x["ai_prob"], reverse=True)[:5]),
        "near_52w_high": [], "near_52w_low": [], "bullish_fib": [], "breadth": {"vix": None, "sectors": []}
    }