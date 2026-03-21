import io
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


def IchimokuCloud(Stock, startDate='2020-01-01', endDate='2021-01-01'):
    # df = yf.download('AAPL', '2019-01-01', '2021-01-01')

    df = yf.download(Stock, startDate, endDate)
    # Define length of Tenkan Sen or Conversion Line
    cl_period = 20

    # Define length of Kijun Sen or Base Line
    bl_period = 60

    # Define length of Senkou Sen B or Leading Span B
    lead_span_b_period = 120

    # Define length of Chikou Span or Lagging Span
    lag_span_period = 30

    # Calculate conversion line
    high_20 = df['High'].rolling(cl_period).max()
    low_20 = df['Low'].rolling(cl_period).min()
    df['conversion_line'] = (high_20 + low_20) / 2

    # Calculate based line
    high_60 = df['High'].rolling(bl_period).max()
    low_60 = df['Low'].rolling(bl_period).min()
    df['base_line'] = (high_60 + low_60) / 2

    # Calculate leading span A
    df['lead_span_A'] = ((df.conversion_line + df.base_line) / 2).shift(lag_span_period)

    # Calculate leading span B
    high_120 = df['High'].rolling(120).max()
    low_120 = df['High'].rolling(120).min()
    df['lead_span_B'] = ((high_120 + low_120) / 2).shift(lead_span_b_period)

    # Calculate lagging span
    df['lagging_span'] = df['Close'].shift(-lag_span_period)

    # Drop NA values from Dataframe
    df.dropna(inplace=True)

    return df[::-1]["base_line"][0]


def WILLIAMS(stock, start='2020-01-01', end='2021-01-01', days=14):
    df = yf.download(stock, start, end)
    highh = df["High"].rolling(days).max()
    lowl = df["Low"].rolling(days).min()
    close = df["Close"]
    wr = -100 * ((highh - close) / (highh - lowl))
    #print(wr[::-1][0])

    return float(wr[::-1][0])
    
    
    
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


def _float_eq(a, b, rtol=1e-9, atol=1e-12):
    """Robust float compare for SuperTrend band transitions (avoids strict == on floats)."""
    try:
        return bool(np.isclose(float(a), float(b), rtol=rtol, atol=atol))
    except (TypeError, ValueError):
        return False


def _supertrend_numpy_on_df(data: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    """
    SuperTrend (same rules as legacy iterrows BOTSingal) via NumPy loops.
    Requires columns High, Low, Close, TR. Sets ATR, BUB, BLB, FUB, FLB, ST, ST_BUY_SELL.
    """
    n = len(data)
    if n == 0:
        return data
    tr = np.asarray(data["TR"].values, dtype=np.float64)
    close = np.asarray(data["Close"].values, dtype=np.float64)
    high = np.asarray(data["High"].values, dtype=np.float64)
    low = np.asarray(data["Low"].values, dtype=np.float64)

    atr = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        atr[i] = (atr[i - 1] * 13.0 + tr[i]) / 14.0

    hl2 = (high + low) / 2.0
    bub = np.round(hl2 + multiplier * atr, 2)
    blb = np.round(hl2 - multiplier * atr, 2)

    fub = np.zeros(n, dtype=np.float64)
    flb = np.zeros(n, dtype=np.float64)
    st = np.zeros(n, dtype=np.float64)

    for i in range(1, n):
        if (bub[i] < fub[i - 1]) or (close[i - 1] > fub[i - 1]):
            fub[i] = bub[i]
        else:
            fub[i] = fub[i - 1]

    for i in range(1, n):
        if (blb[i] > flb[i - 1]) or (close[i - 1] < flb[i - 1]):
            flb[i] = blb[i]
        else:
            flb[i] = flb[i - 1]

    for i in range(1, n):
        if _float_eq(st[i - 1], fub[i - 1]) and close[i] <= fub[i]:
            st[i] = fub[i]
        elif _float_eq(st[i - 1], fub[i - 1]) and close[i] > fub[i]:
            st[i] = flb[i]
        elif _float_eq(st[i - 1], flb[i - 1]) and close[i] >= flb[i]:
            st[i] = flb[i]
        elif _float_eq(st[i - 1], flb[i - 1]) and close[i] < flb[i]:
            st[i] = fub[i]

    st_buy_sell = np.array(["SELL"] * n, dtype=object)
    st_buy_sell[0] = "NA"
    for i in range(1, n):
        if st[i] < close[i]:
            st_buy_sell[i] = "BUY"
        else:
            st_buy_sell[i] = "SELL"

    out = data.copy()
    out["ATR"] = atr
    out["BUB"] = bub
    out["BLB"] = blb
    out["FUB"] = fub
    out["FLB"] = flb
    out["ST"] = st
    out["ST_BUY_SELL"] = st_buy_sell
    return out


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


def fibonacci(stock, start='2020-01-01', end='2021-01-01'):
    df = yf.download(stock, start, end)
    highest_swing = -1
    lowest_swing = -1
    ratios = [0,0.236, 0.382, 0.5 , 0.618, 0.786,1]
    levels = []
    
    for i in range(1,df.shape[0]-1):
        if df['High'][i] > df['High'][i-1] and df['High'][i] > df['High'][i+1] and (highest_swing == -1 or df['High'][i] > df['High'][highest_swing]):
            highest_swing = i

    if df['Low'][i] < df['Low'][i-1] and df['Low'][i] < df['Low'][i+1] and (lowest_swing == -1 or df['Low'][i] < df['Low'][lowest_swing]):
        lowest_swing = i
        
    for ratio in ratios:
        if highest_swing > lowest_swing: # Uptrend
            levels.append(max_level - (max_level-min_level)*ratio)
        else: # Downtrend
            levels.append(min_level + (max_level-min_level)*ratio)

    return levels
    
    
def BOTSingal(data, multiplier=1.0):
    """SuperTrend signal; uses NumPy loops instead of pandas iterrows (hot path)."""
    df = data.copy()
    df["tr0"] = abs(df["High"] - df["Low"])
    df["tr1"] = abs(df["High"] - df["Close"].shift(1))
    df["tr2"] = abs(df["Low"] - df["Close"].shift(1))
    df["TR"] = round(df[["tr0", "tr1", "tr2"]].max(axis=1), 2)
    return _supertrend_numpy_on_df(df, multiplier)
    
    
def alphaTrend(stock, dataSet=None, period="5d", interval="5m"):
    multiplier = 2.0
    if dataSet == None:
        interval = interval[0]
        data = histDataframe(stock, period=period, interval=interval)
        data = data.reset_index(drop=True)
    else:
        totalCandleString = "Date,Open,High,Low,Close,Volume\n" + '\n'.join(each for each in dataSet)
        data_df = io.StringIO(totalCandleString)
        data = pd.read_csv(data_df, sep=",")
    
    data["tr0"] = abs(data["High"] - data["Low"])
    data["tr1"] = abs(data["High"] - data["Close"].shift(1))
    data["tr2"] = abs(data["Low"] - data["Close"].shift(1))
    data["TR"] = round(data[["tr0", "tr1", "tr2"]].max(axis=1), 2)
    return _supertrend_numpy_on_df(data, multiplier)

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
    avg_gain = []
    avg_loss = []
    gain = df['gain'].tolist()
    loss = df['loss'].tolist()
    for i in range(len(df)):
        if i < n:
            avg_gain.append(np.NaN)
            avg_loss.append(np.NaN)
        elif i == n:
            avg_gain.append(df['gain'].rolling(n).mean()[n])
            avg_loss.append(df['loss'].rolling(n).mean()[n])
        elif i > n:
            avg_gain.append(((n - 1) * avg_gain[i - 1] + gain[i]) / n)
            avg_loss.append(((n - 1) * avg_loss[i - 1] + loss[i]) / n)
    df['avg_gain'] = np.array(avg_gain)
    df['avg_loss'] = np.array(avg_loss)
    df['RS'] = df['avg_gain'] / df['avg_loss']
    df['RSI'] = 100 - (100 / (1 + df['RS']))

    return df    
    
    
def rsiOverSMA(ticker, n=20, period="7d", interval="1m", daytrend="None"):
    """New Indicator with multichart Analysis
    this is a little complex 
    calculate over multichart too looking if crossOver happen near momement
    and generating the momementum for a trade for bull/bear moves"""

    DF_3min = histDataframe(ticker, period, interval="3m")
    DF_5min = histDataframe(ticker, period, interval="5m")
    DF_15min = histDataframe(ticker, period, interval="15m")

    rsiDF_3min = getRSICalculate(DF_3min, n)['RSI'][::-1][0]
    rsiDF_5min = getRSICalculate(DF_3min, n)['RSI'][::-1][0]
    rsiDF_15min = getRSICalculate(DF_3min, n)['RSI'][::-1][0]
    
    rsi_3min = rsiDF_3min['RSI'][::-1][0]
    rsi_5min = rsiDF_5min['RSI'][::-1][0]
    rsi_15min = rsiDF_15min['RSI'][::-1][0]
    
    
    smaDF_3min = indi.SMA(rsiDF_3min, column_name="RSI")
    smaDF_5min = indi.SMA(rsiDF_5min, column_name="RSI")
    smaDF_15min = indi.SMA(rsiDF_15min, column_name="RSI")
    
    sma_3min = smaDF_3min['SMA'][::-1][0]
    sma_5min = smaDF_5min['SMA'][::-1][0]
    sma_15min = smaDF_15min['SMA'][::-1][0]
    

    return rsi_3min, rsi_5min, rsi_15min, sma_3min, sma_5min, sma_15min


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


def checkRSIDivergence(df, rsi_period=14, lookback=5):
    """
    Detect RSI divergence. Bullish: price lower low, RSI higher low. Bearish: price higher high, RSI lower high.
    Returns 'bullish', 'bearish', or None.
    """
    if df is None or len(df) < rsi_period + lookback + 2:
        return None
    df = _norm_columns(df)
    if 'close' not in df.columns and 'Close' not in df.columns:
        return None
    df = getRSICalculate(df, rsi_period)
    if 'RSI' not in df.columns or df['RSI'].isna().all():
        return None
    recent = df.tail(lookback + 2)
    close_col = 'close' if 'close' in df.columns else 'Close'
    closes = recent[close_col].values
    rsis = recent['RSI'].values
    if len(closes) < 4 or len(rsis) < 4:
        return None
    # Compare last two swing points
    price_low_0, price_low_1 = min(closes[:2]), min(closes[-2:])
    price_high_0, price_high_1 = max(closes[:2]), max(closes[-2:])
    rsi_low_0, rsi_low_1 = min(rsis[:2]), min(rsis[-2:])
    rsi_high_0, rsi_high_1 = max(rsis[:2]), max(rsis[-2:])
    if price_low_1 < price_low_0 and rsi_low_1 > rsi_low_0:
        return 'bullish'
    if price_high_1 > price_high_0 and rsi_high_1 < rsi_high_0:
        return 'bearish'
    return None


def checkVolumeDivergence(df, lookback=5):
    """
    Detect volume divergence. Bearish: price up, volume down. Bullish: price down, volume rising.
    Returns 'bullish', 'bearish', or None.
    """
    if df is None or len(df) < lookback + 2:
        return None
    df = _norm_columns(df)
    if 'close' not in df.columns and 'Close' not in df.columns:
        return None
    if 'volume' not in df.columns and 'Volume' not in df.columns:
        return None
    recent = df.tail(lookback + 2)
    close_col = 'close' if 'close' in df.columns else 'Close'
    vol_col = 'volume' if 'volume' in df.columns else 'Volume'
    closes = recent[close_col].values
    vols = recent[vol_col].values
    if len(closes) < 3 or len(vols) < 3:
        return None
    price_trend = closes[-1] - closes[0]
    vol_trend = vols[-1] - vols[0]
    if price_trend > 0 and vol_trend < 0:
        return 'bearish'
    if price_trend < 0 and vol_trend > 0:
        return 'bullish'
    return None


def checkLiquiditySwapPattern(df, lookback=5):
    """
    Detect liquidity swap pattern (sweep and reversal).
    Bullish: price sweeps below recent low then closes above (liquidity grab up) — good for CALL.
    Bearish: price sweeps above recent high then closes below (liquidity grab down) — good for PUT.
    Returns 'bullish', 'bearish', or None.
    """
    if df is None or len(df) < lookback + 3:
        return None
    df = _norm_columns(df)
    if 'high' not in df.columns or 'low' not in df.columns or ('close' not in df.columns and 'Close' not in df.columns):
        return None
    close_col = 'close' if 'close' in df.columns else 'Close'
    recent = df.tail(lookback + 2)
    highs = recent['high'].values
    lows = recent['low'].values
    closes = recent[close_col].values
    if len(highs) < 3 or len(lows) < 3 or len(closes) < 3:
        return None
    # Last candle: did it sweep below prior low and close above? (bullish)
    recent_low = min(lows[:-1]) if len(lows) > 1 else lows[0]
    last_low = lows[-1]
    last_close = closes[-1]
    if last_low < recent_low and last_close > recent_low and last_close > (highs[-1] + lows[-1]) / 2:
        return 'bullish'
    # Last candle: did it sweep above prior high and close below? (bearish)
    recent_high = max(highs[:-1]) if len(highs) > 1 else highs[0]
    last_high = highs[-1]
    if last_high > recent_high and last_close < recent_high and last_close < (highs[-1] + lows[-1]) / 2:
        return 'bearish'
    return None


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