import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import warnings

warnings.filterwarnings('ignore')
sia = SentimentIntensityAnalyzer()

METAL_TICKERS = {
    "TATA STEEL": "TATASTEEL.NS", "HINDALCO": "HINDALCO.NS",
    "JSW STEEL": "JSWSTEEL.NS", "VEDANTA": "VEDL.NS",
    "COAL INDIA": "COALINDIA.NS", "NALCO": "NATIONALUM.NS",
    "NMDC": "NMDC.NS", "SAIL": "SAIL.NS",
    "JINDAL STEEL": "JINDALSTEL.NS", "GRAPHITE INDIA": "GRAPHITE.NS"
}

def predict_price(close_history, days):
    try:
        y = close_history.values.reshape(-1, 1)
        x = np.array(range(len(y))).reshape(-1, 1)
        model = LinearRegression().fit(x, y)
        future_day = np.array([[len(y) + days]])
        prediction = model.predict(future_day)[0][0]
        current_price = float(close_history.iloc[-1])
        volatility_buffer = (0.06 * (days / 5)) 
        return min(max(prediction, current_price * (1 - volatility_buffer)), current_price * (1 + volatility_buffer))
    except: return 0

def get_metals_strategy():
    dxy_ticker = "DX-Y.NYB"
    all_tickers = list(METAL_TICKERS.values()) + [dxy_ticker]
    ticker_str = " ".join(all_tickers)
    
    try:
        # Download data with a timeout to prevent hanging
        hist = yf.download(ticker_str, period="6mo", progress=False, timeout=10)
        if hist.empty: raise Exception("No data from Yahoo")

        dxy_closes = hist['Close'][dxy_ticker].dropna()
        dxy_val = float(dxy_closes.iloc[-1]) if not dxy_closes.empty else 100.0
        
        # Shock Monitor: DXY Velocity
        dxy_velocity = 0
        if len(dxy_closes) > 5:
            dxy_velocity = ((dxy_val - dxy_closes.iloc[-5]) / dxy_closes.iloc[-5]) * 100
        
        macro_boost = 20 if dxy_val < 95.0 else 10 if dxy_val < 103.0 else -10
        scored_stocks = []

        for name, ticker in METAL_TICKERS.items():
            try:
                close = hist['Close'][ticker].dropna()
                volume = hist['Volume'][ticker].dropna()
                if len(close) < 30: continue 

                # ML & Predictions
                p_1w = predict_price(close, 5)
                p_3m = predict_price(close, 66)
                
                # KNN Probability
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rsi = 100 - (100 / (1 + (gain / loss))).fillna(50)

                df = pd.DataFrame({'RSI': rsi, 'Vol': volume, 'Close': close}).dropna()
                df['Target'] = (df['Close'].shift(-3) > df['Close']).astype(int)
                df = df.dropna()
                
                prob = 50 # Default
                if not df.empty:
                    X_s = StandardScaler().fit_transform(df[['RSI', 'Vol']].values)
                    knn = KNeighborsClassifier(n_neighbors=5).fit(X_s, df['Target'].values)
                    today_feat = X_s[-1].reshape(1, -1)
                    prob = knn.predict_proba(today_feat)[0][1] * 100

                total_score = prob + macro_boost
                total_score = min(max(total_score, 0), 100)

                if total_score >= 75: action, color = "STRONG BUY", "#02c076"
                elif total_score >= 55: action, color = "ACCUMULATE", "#17a2b8"
                else: action, color = "HOLD / WATCH", "#f0b90b"

                scored_stocks.append({
                    "name": name, "score": total_score, "algo_action": action, "algo_color": color,
                    "pred_1w": f"₹{p_1w:,.2f}", "pred_3m": f"₹{p_3m:,.2f}"
                })
            except: continue

        return {
            "dxy_val": f"{dxy_val:.2f}",
            "dxy_trend": "SPIKING" if dxy_velocity > 0.1 else "STABLE",
            "stocks": sorted(scored_stocks, key=lambda x: x['score'], reverse=True)
        }
    except Exception as e:
        print(f"Metals Strategy Error: {e}")
        return {"dxy_val": "N/A", "dxy_trend": "OFFLINE", "stocks": []}

def get_metals_ticks():
    ticker_str = " ".join(METAL_TICKERS.values())
    try:
        hist = yf.download(ticker_str, period="2d", progress=False, timeout=5)
        ticks = {}
        for name, ticker in METAL_TICKERS.items():
            try:
                c = hist['Close'][ticker].dropna()
                v = hist['Volume'][ticker].dropna()
                val = float(c.iloc[-1])
                chg = ((val - c.iloc[-2]) / c.iloc[-2]) * 100
                ticks[name.replace(" ", "-")] = {
                    "ltp": f"₹{val:,.2f}", "chg": f"{chg:+.2f}%", 
                    "raw_chg": chg, "volume": f"{v.iloc[-1]:,.0f}"
                }
            except: continue
        return ticks
    except: return {}