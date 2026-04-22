import os
import threading
import requests
from flask import Flask, render_template, jsonify
from dhanhq import dhanhq, marketfeed
import nsepython
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
from datetime import datetime
import warnings
from bs4 import XMLParsedAsHTMLWarning
from news import get_news_feed
from market_metric import get_market_metrics
from metals_engine import get_metals_strategy, get_metals_ticks
from screener_engine import build_dynamic_dhan_universe

# Tell Python to ignore that specific BeautifulSoup warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

app = Flask(__name__)
sia = SentimentIntensityAnalyzer()

# Credentials
client_id = "2604202082"
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc2OTU1MzQ3LCJpYXQiOjE3NzY4Njg5NDcsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTEwNTY5OTkwIn0.zzsRiicO523mz9nwMUiR3BQi-_WwMY0unHPkuoTZ7DmKiEcQzXS8T5B-cOMc23f2O9GM8WxAIfv86K9SqOccEA"
dhan = dhanhq(client_id, access_token)

live_strategy_data = {}

def on_message(instance, message):
    global live_strategy_data
    sec_id = str(message.get('security_id'))
    live_strategy_data[sec_id] = {"ltp": message.get('last_price'), "oi": message.get('oi')}

@app.route('/')
def index():
    return render_template('index.html')

# 🎯 YOUR NEWS ROUTE IS NOW JUST 3 LINES LONG
@app.route('/api/news')
def api_news():
    """Calls the external ML News Engine"""
    news_data = get_news_feed()
    return jsonify(news_data)

@app.route('/api/scan_strategy')
def scan_strategy():
    try:
        exp = dhan.get_expiry_list(13, "IDX_I")['data'][0]
        oc_data = dhan.get_option_chain(13, "IDX_I", exp).get('data', {})
        
        oc_ltp = float(oc_data.get('last_price') or 0)
        if oc_ltp == 0:
            oc_ltp = float(dhan.get_ltp_data("NSE", "IDX", "Nifty 50").get('data', {}).get('last_price', 22000))

        strikes = []
        inst = []
        for strike, details in oc_data.get('oc', {}).items():
            if abs(float(strike) - oc_ltp) <= 250:
                ce, pe = details.get('ce', {}), details.get('pe', {})
                strikes.append({"strike": strike, "ce_id": ce.get('security_id'), "pe_id": pe.get('security_id'), 
                                "total_vol": ce.get('volume', 0) + pe.get('volume', 0), "ce_ltp": ce.get('last_price', 0), "pe_ltp": pe.get('last_price', 0)})
        
        top = sorted(strikes, key=lambda x: x['total_vol'], reverse=True)[:6]
        
        for s in top:
            if s['ce_id']: inst.append((marketfeed.NSE_FNO, str(s['ce_id']), marketfeed.Full))
            if s['pe_id']: inst.append((marketfeed.NSE_FNO, str(s['pe_id']), marketfeed.Full))
            
        feed = marketfeed.DhanFeed(client_id, access_token, inst, on_connect=lambda x: print("Feed ON"), on_message=on_message)
        threading.Thread(target=feed.run_forever, daemon=True).start()
        
        return jsonify(top)
    except Exception as e:
        print(f"Strategy Error: {e}")
        # 🎯 FIX: Return empty list safely
        return jsonify([])

@app.route('/api/metrics')
def api_metrics():
    """Calls the external Market Metrics Engine"""
    # No longer passing the 'dhan' client. The engine is self-sufficient!
    metrics_data = get_market_metrics()
    return jsonify(metrics_data)


@app.route('/api/portfolio')
def api_portfolio():
    funds = dhan.get_fund_limits().get('data', {})
    pos = dhan.get_positions().get('data', [])
    pnl = sum(float(p.get('unrealizedProfit', 0)) + float(p.get('realizedProfit', 0)) for p in pos)
    return jsonify({
        "balance": f"₹{float(funds.get('availabelBalance',0)):,.2f}",
        "pnl": f"₹{pnl:,.2f}",
        "pnl_class": "BULLISH" if pnl >= 0 else "BEARISH",
        "positions": pos,
        "orders": dhan.get_order_list().get('data', [])
    })

@app.route('/api/live_ticks')
def get_ticks(): return jsonify(live_strategy_data)

@app.route('/api/metals_strategy')
def api_metals_strategy():
    """Predictive Algorithm for Metal Stocks based on DXY"""
    data = get_metals_strategy()
    return jsonify(data)
@app.route('/api/metals_ticks')
def api_metals_ticks():
    """Lightning fast LTP ticker for the Metals UI"""
    return jsonify(get_metals_ticks())

@app.route('/api/screener')
def api_screener():
    return jsonify(build_dynamic_dhan_universe())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)