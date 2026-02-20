import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

class ScalpingStrategy:
    def __init__(self, keltner_period=20, keltner_multiplier=1.5, rsi_period=5, adx_period=14, adx_threshold=25, volume_ma_period=20, pip_size=0.0001):
        self.keltner_period = keltner_period
        self.keltner_multiplier = keltner_multiplier
        self.rsi_period = rsi_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.volume_ma_period = volume_ma_period
        self.pip_size = pip_size

    def calculate_indicators(self, df):
        df = df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['sma_20'] = df['Close'].rolling(window=self.keltner_period).mean()
        df['tr'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
        df['atr'] = df['tr'].rolling(window=self.keltner_period).mean()
        df['upper_band'] = df['sma_20'] + (self.keltner_multiplier * df['atr'])
        df['lower_band'] = df['sma_20'] - (self.keltner_multiplier * df['atr'])
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = abs(minus_dm)
        tr_rolling = df['tr'].rolling(window=self.adx_period).sum()
        plus_di = 100 * (plus_dm.rolling(window=self.adx_period).sum() / tr_rolling)
        minus_di = 100 * (minus_dm.rolling(window=self.adx_period).sum() / tr_rolling)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df['adx'] = dx.rolling(window=self.adx_period).mean()
        df['avg_volume'] = df['Volume'].rolling(window=self.volume_ma_period).mean()
        df['support_20'] = df['Low'].rolling(window=20).min()
        df['resistance_20'] = df['High'].rolling(window=20).max()
        df['resistance_10'] = df['High'].rolling(window=10).max()
        df['support_10'] = df['Low'].rolling(window=10).min()
        df['recent_low_5'] = df['Low'].rolling(window=5).min()
        df['recent_high_5'] = df['High'].rolling(window=5).max()
        return df

class Backtester:
    def __init__(self, initial_balance=1000, lot_size=100000):
        self.balance = initial_balance
        self.lot_size = lot_size
        self.trades = []
        self.active_trade = None

    def run(self, df, strategy):
        df = strategy.calculate_indicators(df)
        for i in range(30, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            timestamp = df.index[i]
            if self.active_trade:
                self.manage_active_trade(row, timestamp)
                continue
            signal = self.check_entry(row, prev_row, strategy)
            if signal:
                self.open_trade(signal, row, timestamp, strategy)
        return self.get_report(), pd.DataFrame(self.trades)

    def check_entry(self, row, prev_row, strategy):
        # Extremely relaxed for demonstration simulation
        if (row['Close'] <= row['lower_band']):
            if (row['rsi'] < 40):
                return 'BUY'
        if (row['Close'] >= row['upper_band']):
            if (row['rsi'] > 60):
                return 'SELL'
        return None

    def open_trade(self, side, row, timestamp, strategy):
        entry_price = row['Close']
        sl = row['recent_low_5'] - (2 * strategy.pip_size) if side == 'BUY' else row['recent_high_5'] + (2 * strategy.pip_size)
        self.active_trade = {'side': side, 'entry_price': entry_price, 'sl': sl, 'entry_time': timestamp, 'is_half_closed': False}

    def manage_active_trade(self, row, timestamp):
        trade = self.active_trade
        current_price = row['Close']
        if trade['side'] == 'BUY':
            if current_price <= trade['sl']: self.close_trade(current_price, timestamp, "SL")
            elif (current_price - trade['entry_price']) / 0.0001 >= 10: self.close_trade(current_price, timestamp, "TP")
        else:
            if current_price >= trade['sl']: self.close_trade(current_price, timestamp, "SL")
            elif (trade['entry_price'] - current_price) / 0.0001 >= 10: self.close_trade(current_price, timestamp, "TP")

    def close_trade(self, exit_price, timestamp, reason):
        trade = self.active_trade
        pnl = (exit_price - trade['entry_price']) if trade['side'] == 'BUY' else (trade['entry_price'] - exit_price)
        self.balance += pnl * self.lot_size
        self.trades.append({'side': trade['side'], 'entry': trade['entry_price'], 'exit': exit_price, 'pnl': pnl * self.lot_size, 'reason': reason, 'time': timestamp})
        self.active_trade = None

    def get_report(self):
        if not self.trades: return "No trades executed."
        df_t = pd.DataFrame(self.trades)
        return {'Total Trades': len(df_t), 'Total Profit ($)': round(df_t['pnl'].sum(), 2), 'Win Rate (%)': round((df_t['pnl'] > 0).sum() / len(df_t) * 100, 2), 'Final Balance ($)': round(self.balance, 2)}

def plot_results(df, trades_df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    if not trades_df.empty:
        for _, t in trades_df.iterrows():
            fig.add_trace(go.Scatter(x=[t['time']], y=[t['exit']], mode='markers', marker=dict(color='green' if t['pnl']>0 else 'red', size=10), name='Trade'), row=1, col=1)
    fig.update_layout(title='EUR/USD Scalping Simulation', xaxis_rangeslider_visible=False, height=600)
    fig.write_html("/home/ubuntu/simulation_results.html")

if __name__ == "__main__":
    data = yf.download("EURUSD=X", period="1mo", interval="1h")
    if not data.empty:
        report, trades = Backtester().run(data, ScalpingStrategy(adx_threshold=10))
        print(report)
        plot_results(data, trades)
