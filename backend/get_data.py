import requests 
import pandas as pd 


def get_binance_klines(symbol='BTCUSDT', interval='1m', start_time=None, end_time=None, limit=1000):
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': limit
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base volume', 'Taker buy quote volume', 'Ignore'
    ])
    
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    
    cols_to_convert = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[cols_to_convert] = df[cols_to_convert].astype(float)

    df = df[['Open time', 'Open', 'High', 'Low', 'Close', 'Volume']]
    return df