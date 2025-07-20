import yfinance as yf
import pandas as pd
import numpy as np

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
    

def EMA_8_13_21(stock, PRICE_NAME="Close", period="5d", interval="1m", period1=8, period2=13, period3=21):    
    pdData = histDataframe(ticker=stock, period=period, interval=interval)
    
    EMA_8_days = pdData[PRICE_NAME].ewm(span=period1, adjust=False).mean()
    EMA_13_days = pdData[PRICE_NAME].ewm(span=period2, adjust=False).mean()
    EMA_21_days = pdData[PRICE_NAME].ewm(span=period3, adjust=False).mean()
    
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
    multiplier = multiplier
    data['tr0'] = abs(data["High"] - data["Low"])
    data['tr1'] = abs(data["High"] - data["Close"].shift(1))
    data['tr2'] = abs(data["Low"] - data["Close"].shift(1))
    data["TR"] = round(data[['tr0', 'tr1', 'tr2']].max(axis=1), 2)
    data["ATR"] = 0.00
    data['BUB'] = 0.00
    data["BLB"] = 0.00
    data["FUB"] = 0.00
    data["FLB"] = 0.00
    data["ST"] = 0.00

    # Calculating ATR
    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, 'ATR'] = 0.00
        else:
            data.loc[i, 'ATR'] = (
                (data.loc[i-1, 'ATR'] * 13) + data.loc[i, 'TR']) / 14

    data['BUB'] = round(
        ((data["High"] + data["Low"]) / 2) + (multiplier * data["ATR"]), 2)
    data['BLB'] = round(
        ((data["High"] + data["Low"]) / 2) - (multiplier * data["ATR"]), 2)

    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, "FUB"] = 0.00
        else:
            if (data.loc[i, "BUB"] < data.loc[i-1, "FUB"]) or (data.loc[i-1, "Close"] > data.loc[i-1, "FUB"]):
                data.loc[i, "FUB"] = data.loc[i, "BUB"]
            else:
                data.loc[i, "FUB"] = data.loc[i-1, "FUB"]

    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, "FLB"] = 0.00
        else:
            if (data.loc[i, "BLB"] > data.loc[i-1, "FLB"]) | (data.loc[i-1, "Close"] < data.loc[i-1, "FLB"]):
                data.loc[i, "FLB"] = data.loc[i, "BLB"]
            else:
                data.loc[i, "FLB"] = data.loc[i-1, "FLB"]

    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, "ST"] = 0.00
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FUB"]) & (data.loc[i, "Close"] <= data.loc[i, "FUB"]):
            data.loc[i, "ST"] = data.loc[i, "FUB"]
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FUB"]) & (data.loc[i, "Close"] > data.loc[i, "FUB"]):
            data.loc[i, "ST"] = data.loc[i, "FLB"]
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FLB"]) & (data.loc[i, "Close"] >= data.loc[i, "FLB"]):
            data.loc[i, "ST"] = data.loc[i, "FLB"]
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FLB"]) & (data.loc[i, "Close"] < data.loc[i, "FLB"]):
            data.loc[i, "ST"] = data.loc[i, "FUB"]

    # Buy Sell Indicator
    for i, row in data.iterrows():
        if i == 0:
            data["ST_BUY_SELL"] = "NA"
        elif (data.loc[i, "ST"] < data.loc[i, "Close"]):
            data.loc[i, "ST_BUY_SELL"] = "BUY"
        else:
            data.loc[i, "ST_BUY_SELL"] = "SELL"
    print("Value of signal is = {}".format(data))

    return data
    
    
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
    
    data['tr0'] = abs(data["High"] - data["Low"])
    data['tr1'] = abs(data["High"] - data["Close"].shift(1))
    data['tr2'] = abs(data["Low"] - data["Close"].shift(1))
    data["TR"] = round(data[['tr0', 'tr1', 'tr2']].max(axis=1), 2)
    data["ATR"] = 0.00
    data['BUB'] = 0.00
    data["BLB"] = 0.00
    data["FUB"] = 0.00
    data["FLB"] = 0.00
    data["ST"] = 0.00

    # Calculating ATR
    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, 'ATR'] = 0.00
        else:
            data.loc[i, 'ATR'] = (
                (data.loc[i-1, 'ATR'] * 13) + data.loc[i, 'TR']) / 14

    data['BUB'] = round(
        ((data["High"] + data["Low"]) / 2) + (multiplier * data["ATR"]), 2)
    data['BLB'] = round(
        ((data["High"] + data["Low"]) / 2) - (multiplier * data["ATR"]), 2)

    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, "FUB"] = 0.00
        else:
            if (data.loc[i, "BUB"] < data.loc[i-1, "FUB"]) or (data.loc[i-1, "Close"] > data.loc[i-1, "FUB"]):
                data.loc[i, "FUB"] = data.loc[i, "BUB"]
            else:
                data.loc[i, "FUB"] = data.loc[i-1, "FUB"]

    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, "FLB"] = 0.00
        else:
            if (data.loc[i, "BLB"] > data.loc[i-1, "FLB"]) | (data.loc[i-1, "Close"] < data.loc[i-1, "FLB"]):
                data.loc[i, "FLB"] = data.loc[i, "BLB"]
            else:
                data.loc[i, "FLB"] = data.loc[i-1, "FLB"]

    for i, row in data.iterrows():
        if i == 0:
            data.loc[i, "ST"] = 0.00
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FUB"]) & (data.loc[i, "Close"] <= data.loc[i, "FUB"]):
            data.loc[i, "ST"] = data.loc[i, "FUB"]
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FUB"]) & (data.loc[i, "Close"] > data.loc[i, "FUB"]):
            data.loc[i, "ST"] = data.loc[i, "FLB"]
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FLB"]) & (data.loc[i, "Close"] >= data.loc[i, "FLB"]):
            data.loc[i, "ST"] = data.loc[i, "FLB"]
        elif (data.loc[i-1, "ST"] == data.loc[i-1, "FLB"]) & (data.loc[i, "Close"] < data.loc[i, "FLB"]):
            data.loc[i, "ST"] = data.loc[i, "FUB"]

    # Buy Sell Indicator
    for i, row in data.iterrows():
        if i == 0:
            data["ST_BUY_SELL"] = "NA"
        elif (data.loc[i, "ST"] < data.loc[i, "Close"]):
            data.loc[i, "ST_BUY_SELL"] = "BUY"
        else:
            data.loc[i, "ST_BUY_SELL"] = "SELL"
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