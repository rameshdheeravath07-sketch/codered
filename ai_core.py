import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import warnings

warnings.filterwarnings('ignore')

def calculate_advanced_signals(df):
    """Hybrid AI: Detects the 'Pulse' before a breakout."""
    try:
        if len(df) < 30:
            return 50.0, float(df['Close'].iloc[-1]), 1.0

        # Physics Features
        df['vol_vel'] = df['Volume'].iloc[-5:].mean() / df['Volume'].iloc[-30:-5].mean()
        df['squeeze'] = (df['High'].rolling(20).max() - df['Low'].rolling(20).min()) / df['Close'] * 100
        df['res_dist'] = (df['High'].rolling(60).max() - df['Close']) / df['Close'] * 100
        
        # Institutional Pulse
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
        df['vwap_dist'] = (df['Close'] - df['vwap']) / df['vwap'] * 100

        # AI Targets
        df['Target'] = (df['Close'].shift(-10) > df['Close'] * 1.01).astype(int)
        train_df = df.dropna()

        if len(train_df) < 10 or len(np.unique(train_df['Target'])) < 2:
            return 55.0, float(df['Close'].iloc[-1] * 1.01), float(df['vol_vel'].iloc[-1])

        features = ['vol_vel', 'squeeze', 'res_dist', 'vwap_dist']
        X = train_df[features].values
        y = train_df['Target'].values
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = XGBClassifier(n_estimators=30, max_depth=3, verbosity=0)
        model.fit(X_scaled, y)
        
        current_X = scaler.transform([df[features].iloc[-1].values])
        prob = model.predict_proba(current_X)[0][1] * 100
        
        return float(prob), float(df['Close'].iloc[-1] * 1.015), float(df['vol_vel'].iloc[-1])

    except Exception as e:
        print(f"⚠️ AI Core Error: {e}")
        return 50.0, 0.0, 1.0