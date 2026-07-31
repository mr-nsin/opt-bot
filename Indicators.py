import yfinance as yf
import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
except ImportError:
    ta = None

data = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close'])


##################################################################################################################################################
################################### TOD-DO ADD DATAFRAME OF TWS DATA IN EVERY INDICATOR FUNCTION PARAMETER #######################################
##################################################################################################################################################

def histDataframe(ticker, period="5d", interval='1m'):
    sym = yf.Ticker(ticker)
    sym_data = sym.history(period=period, interval=interval, actions=False)
    return sym_data


#class Indicators:

def RSI(ticker, n=20, period="2y", interval="1d"):
    """function to calculate RSI"""
    n = int(n)
    DF = histDataframe(ticker, period, interval)
    df = getRSICalculate(DF, n)

    return df


def OBV(stock, start='2020-12-01', end='2021-12-01', days=14):
    df = yf.download(stock, start, end)
    obv = []
    obv.append(0)
    for i in range(1, len(df["Close"])):
        if df["Close"][i] > df["Close"][i - 1]:
            obv.append(obv[-1] + df["Volume"][i])
        elif df["Close"][i] < df["Close"][i - 1]:
            obv.append(obv[-1] - df["Volume"][i])
        else:
            obv.append(obv[-1])

    #print(obv[::-1][0])
    return int(obv[::-1][0])


def MACD(stock, start='2020-01-01', end='2021-01-01', PRICE_NAME="Close", period1=26, period2=12, period3=9):
    df = yf.download(stock, start, end)
    EMA_1 = df[PRICE_NAME].ewm(span=period1, adjust=False).mean()
    EMA_2 = df[PRICE_NAME].ewm(span=period2, adjust=False).mean()
    MACD_line = EMA_2 - EMA_1
    MACD_Signal_line = MACD_line.ewm(span=period3, adjust=False).mean()
    MACD_Histogram = MACD_line - MACD_Signal_line
    #print(MACD_line, MACD_Signal_line, MACD_Histogram)

    return MACD_line[::-1][0]



def SMA(DF, days=14, column_name="Close"):
    """function to calculate SMA"""
    print("SMA TO CALCULATE FOR NUMBER OF DAYS IS = {}".format(days))
    df = DF.copy()
    df["SMA"] = df[column_name].rolling(days).mean()

    return df
    


def EMA_8_13_21(df):
    EMA_8_days = df["close"].ewm(span=8, adjust=False).mean()
    EMA_13_days = df["close"].ewm(span=13, adjust=False).mean()
    EMA_21_days = df["close"].ewm(span=21, adjust=False).mean()
    return EMA_8_days, EMA_13_days, EMA_21_days

    
def EMA_8_13_21_Ratio(stock, start='2022-01-01', end='2022-01-01', PRICE_NAME="Close", period1=8, period2=13, period3=21):
    df = yf.download(stock, start, end)
    
    EMA_8_days = df[PRICE_NAME].ewm(span=period1, adjust=False).mean()
    EMA_13_days = df[PRICE_NAME].ewm(span=period2, adjust=False).mean()
    EMA_21_days = df[PRICE_NAME].ewm(span=period3, adjust=False).mean()
    # TO-DO
    return EMA_8_days, EMA_13_days, EMA_21_days
    
    
def wwma(values, n):
    return values.ewm(alpha=1/n, min_periods=n, adjust=False).mean()


def ATR(stock, start='2020-01-01', end='2021-01-01', numDays=10):
    df = yf.download(stock, start, end)
    data=df.copy()
    high = data["High"]
    low = data["Low"]
    close = data["Close"]
    data["tr0"] = abs(high-low)
    data["tr1"] = abs(high-close.shift())
    data["tr2"] = abs(low-close.shift())
    tr = data[['tr0', 'tr1', 'tr2']].max(axis=1)
    atr = wwma(tr, numDays)
    return atr



def BOTSingal(data, multiplier=1.0):
    data = data.copy()
    data['tr0'] = abs(data["High"] - data["Low"])
    data['tr1'] = abs(data["High"] - data["Close"].shift(1))
    data['tr2'] = abs(data["Low"] - data["Close"].shift(1))
    data["TR"] = round(data[['tr0', 'tr1', 'tr2']].max(axis=1), 2)
    
    # Calculate ATR vectorized (Wilder's Smoothing)
    data['ATR'] = data['TR'].ewm(alpha=1/14, min_periods=1, adjust=False).mean()
    data['ATR'] = data['ATR'].round(2)
    data.loc[0, 'ATR'] = 0.00 if len(data) > 0 else 0.0

    data['BUB'] = round(((data["High"] + data["Low"]) / 2) + (multiplier * data["ATR"]), 2)
    data['BLB'] = round(((data["High"] + data["Low"]) / 2) - (multiplier * data["ATR"]), 2)

    # Convert to numpy arrays for fast iteration
    bub = data['BUB'].values
    blb = data['BLB'].values
    close = data['Close'].values
    
    n = len(data)
    fub = np.zeros(n)
    flb = np.zeros(n)
    st = np.zeros(n)
    st_buy_sell = np.empty(n, dtype=object)
    
    if n > 0:
        fub[0] = 0.0
        flb[0] = 0.0
        st[0] = 0.0
        st_buy_sell[0] = "NA"
        
        for i in range(1, n):
            # FUB
            if (bub[i] < fub[i-1]) or (close[i-1] > fub[i-1]):
                fub[i] = bub[i]
            else:
                fub[i] = fub[i-1]
                
            # FLB
            if (blb[i] > flb[i-1]) or (close[i-1] < flb[i-1]):
                flb[i] = blb[i]
            else:
                flb[i] = flb[i-1]
                
            # ST
            if (st[i-1] == fub[i-1]) and (close[i] <= fub[i]):
                st[i] = fub[i]
            elif (st[i-1] == fub[i-1]) and (close[i] > fub[i]):
                st[i] = flb[i]
            elif (st[i-1] == flb[i-1]) and (close[i] >= flb[i]):
                st[i] = flb[i]
            elif (st[i-1] == flb[i-1]) and (close[i] < flb[i]):
                st[i] = fub[i]
            else:
                st[i] = 0.00
                
            # Buy Sell
            if st[i] < close[i]:
                st_buy_sell[i] = "BUY"
            else:
                st_buy_sell[i] = "SELL"
                
    data['FUB'] = fub
    data['FLB'] = flb
    data['ST'] = st
    data['ST_BUY_SELL'] = st_buy_sell

    return data
    
    


############# TO-DO #########################################
def getAllPrices(stock, period, interval):
    data = yf.download(stock, period=period, interval=interval)
    
    return data
############# TO-DO #########################################

    
def EMA_CustomSignal(stock, multiPeriod=["1d", "7d", "30d", "90d"], multiInterval=["5m", "15m", "60m", "1d"]):
    # Run in Thread to collect all data at same time
    
    stockList = [stock for i in range(len(multiPeriod))]

    with Pool(len(tickerList)) as proc:
        fullData1 = proc.map(getAllPrices, [(stock, period, interval) for stock, period, interval in zip(stockList, multiPeriod, multiInterval)])
    print("\nFINAL FULL DATA ALL PRICES IS = {}\n".format(fullData1))
    
    # TO- DO Add Code for Candles Length
    # TO- DO Add Code for Candles Up/Down Time
    # TO- DO Add Code for Candles Gain/Loss
    # TO- DO Add Code for Candles EMA Difference
    
    # TO- DO Add Code for EMA Signal received from above 4 to-do and volumne changes
    return ""


def getRSICalculate(DF, n):
    df = DF.copy()
    df['delta'] = df['Close'] - df['Close'].shift(1)
    df['gain'] = np.where(df['delta'] >= 0, df['delta'], 0)
    df['loss'] = np.where(df['delta'] < 0, abs(df['delta']), 0)
    
    # Vectorized Wilder's moving average (equivalent to alpha=1/n ewm)
    df['avg_gain'] = df['gain'].ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    df['avg_loss'] = df['loss'].ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    
    df['RS'] = df['avg_gain'] / df['avg_loss']
    df['RSI'] = 100 - (100 / (1 + df['RS']))

    return df
    
    



def _norm_columns(df):
    """Normalize column names to lowercase; add Close/Volume for compatibility."""
    df = df.copy()
    df.columns = [str(c).lower() if isinstance(c, str) else c for c in df.columns]
    if 'close' in df.columns and 'Close' not in df.columns:
        df['Close'] = df['close']
    if 'volume' in df.columns and 'Volume' not in df.columns:
        df['Volume'] = df['volume']
    return df


def getADX(df, period=14):
    """Calculate ADX (Average Directional Index). Returns last ADX value or None if insufficient data."""
    if ta is None or df is None or len(df) < period + 10:
        return None
    df = _norm_columns(df)
    if 'high' not in df.columns or 'low' not in df.columns or ('close' not in df.columns and 'Close' not in df.columns):
        return None
    close_col = df['close'] if 'close' in df.columns else df['Close']
    adx = ta.adx(df['high'], df['low'], close_col, length=period)
    if adx is None or len(adx) == 0 or pd.isna(adx.iloc[-1]):
        return None
    return float(adx.iloc[-1])





def checkLiquidity(bid, ask, last, volume, min_volume=20, max_spread_pct=15):
    """
    Check if option has sufficient liquidity. Returns True if liquid, False if illiquid.
    """
    if bid is None or bid <= 0:
        bid = last or 0
    if ask is None or ask <= 0:
        ask = last or 0
    mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else (last or 0)
    if mid <= 0:
        return False
    spread = ask - bid if (bid > 0 and ask > 0) else 0
    spread_pct = (spread / mid) * 100 if mid > 0 else 100
    if volume is not None and volume >= 0 and volume < min_volume:
        return False
    if spread_pct > max_spread_pct:
        return False
    return True