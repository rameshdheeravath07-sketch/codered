import yfinance as yf

def get_market_metrics():
    """Unified ultra-fast metric fetcher using yfinance for ALL data."""
    dashboard_data = []

    # Map all categories, adding $ or ₹ identifiers
    global_map = {
        "INDIA EQUITIES": {
            "color": "#f0b90b",
            # 🎯 Added NIFTY BANK (^NSEBANK) right between Nifty 50 and Sensex
            "tickers": {"NIFTY 50": "^NSEI", "NIFTY BANK": "^NSEBANK", "BSE SENSEX": "^BSESN"}
        },
        "INDIAN ADRs (US)": {
            "color": "#17a2b8", 
            "tickers": {"HDFC Bank ($)": "HDB", "ICICI Bank ($)": "IBN", "Infosys ($)": "INFY"}
        },
        "GLOBAL MACRO": {
            "color": "#007bff", 
            "tickers": {"USD/INR (₹)": "INR=X", "Dollar (DXY)": "DX-Y.NYB", "US 10Y Yield (%)": "^TNX", "CBOE VIX": "^VIX", "MSCI EM Index": "EEM"}
        },
        "GLOBAL COMMODITIES": {
            "color": "#f6465d", 
            "tickers": {"Brent Crude ($)": "BZ=F", "WTI Crude ($)": "CL=F", "Gold ($)": "GC=F", "Silver ($)": "SI=F"}
        }
    }
    
    try:
        # 🎯 Bulk Fetch: Added ^NSEBANK to the massive download string
        ticker_str = "^NSEI ^NSEBANK ^BSESN HDB IBN INFY INR=X DX-Y.NYB ^TNX ^VIX EEM BZ=F CL=F GC=F SI=F"
        hist = yf.download(ticker_str, period="2d", progress=False)
        
        for cat, details in global_map.items():
            cat_items = []
            for name, ticker in details["tickers"].items():
                try:
                    # Clean up the name for the UI
                    display_name = name.replace(" ($)", "").replace(" (₹)", "")
                    
                    # Determine if we should prefix with the $ or ₹ symbol
                    prefix = "$" if "($)" in name else "₹" if "(₹)" in name else ""
                    
                    closes = hist['Close'][ticker].dropna()
                    if len(closes) >= 2:
                        val = float(closes.iloc[-1])
                        prev = float(closes.iloc[-2])
                        chg = ((val - prev) / prev) * 100
                        cat_items.append({"name": display_name, "value": f"{prefix}{val:,.2f}", "chg": f"{chg:.2f}"})
                    elif len(closes) == 1:
                        val = float(closes.iloc[-1])
                        cat_items.append({"name": display_name, "value": f"{prefix}{val:,.2f}", "chg": "0.00"})
                except Exception:
                    cat_items.append({"name": name.replace(" ($)", "").replace(" (₹)", ""), "value": "N/A", "chg": "0.00"})
                    
            dashboard_data.append({"category": cat, "color": details["color"], "items": cat_items})
            
    except Exception as e:
        print(f"Metrics Engine Error: {e}")
        
    return dashboard_data