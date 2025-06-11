import pandas_ta as ta 
import pandas as pd 

def preprocess(df_stick, threshold=0.5):

    rsi_feature=ta.rsi(df_stick.Close)
    atr_feature=ta.atr(df_stick.High,df_stick.Low,df_stick.Close)
    adx_feature=ta.adx(df_stick.High,df_stick.Low,df_stick.Close)
    sma_feature=ta.sma(df_stick.Close)
    skew_feature=ta.skew(df_stick.Close)
    slope_feature=ta.slope(df_stick.Close)
    bband_feature=ta.bbands(df_stick.Close).iloc[:,[0,2]]
    macd_feature=ta.macd(df_stick.Close).iloc[:,[0,2]]

    df_stick=pd.concat([df_stick.iloc[:,:-1],sma_feature,rsi_feature,atr_feature,adx_feature,skew_feature,slope_feature,bband_feature,macd_feature,df_stick.iloc[:,-1]],axis=1)
    df_stick=df_stick.dropna()
    df_stick = df_stick[["Low", "High","Close","SMA_10","RSI_14","ATRr_14", "ADX_14",
                          "DMP_14", "DMN_14", "SKEW_30", "SLOPE_1", "BBL_5_2.0", "BBU_5_2.0", 
                          "MACD_12_26_9","MACDs_12_26_9"] ]
    return df_stick