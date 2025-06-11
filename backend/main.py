# from fastapi import FastAPI, Request,Response
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field
# import pickle
# import pandas as pd 
# from datetime import datetime
# import numpy as np 
# from prometheus_fastapi_instrumentator import Instrumentator
# from prometheus_client import Gauge
# import prometheus_client
# from fastapi.templating import Jinja2Templates
# from fastapi.responses import HTMLResponse


# class InputItem(BaseModel):
#     Low: float
#     High: float
#     Close: float
#     SMA_10: float
#     RSI_14: float
#     ATRr_14: float
#     ADX_14: float
#     DMP_14: float
#     DMN_14: float
#     SKEW_30: float
#     SLOPE_1: float
#     BBL_5_2_0: float = Field(alias="BBL_5_2.0")
#     BBU_5_2_0: float = Field(alias="BBU_5_2.0")
#     MACD_12_26_9: float
#     MACDs_12_26_9: float


# app = FastAPI() 
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# templates = Jinja2Templates(directory="template")

# model_dir = "./model/model.pkl"
# with open (model_dir, mode='rb' ) as file: 
#     model = pickle.load(file)


# @app.get("/", response_class=HTMLResponse)
# def read_root(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})
# conf_gauge = Gauge('prediction_confidence', 'Confidence score of the prediction')
# @app.post("/predict")
# def predict(data: InputItem):
#     arr = np.array([
#         [
#             data.Low,
#             data.High,
#             data.Close,
#             data.SMA_10, 
#             data.RSI_14, 
#             data.ATRr_14, 
#             data.ADX_14, 
#             data.DMP_14, 
#             data.DMN_14, 
#             data.SKEW_30, 
#             data.SLOPE_1, 
#             data.BBL_5_2_0, 
#             data.BBU_5_2_0, 
#             data.MACD_12_26_9, 
#             data.MACDs_12_26_9
#         ]
#     ])
#     pred = model.predict(arr)[0]
#     confidence_score= model.predict_proba(arr)[0][pred]
#     conf_gauge.set(confidence_score)
#     return {'prediction':int(pred)}

# @app.get("/metrics")
# def metrics():

#     return Response(
#         content=prometheus_client.generate_latest(),
#         media_type='text/plain'
#     )

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pickle
import pandas as pd 
from datetime import datetime
import numpy as np 
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Gauge, Histogram
import prometheus_client
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import time

class InputItem(BaseModel):
    Low: float
    High: float
    Close: float
    SMA_10: float
    RSI_14: float
    ATRr_14: float
    ADX_14: float
    DMP_14: float
    DMN_14: float
    SKEW_30: float
    SLOPE_1: float
    BBL_5_2_0: float = Field(alias="BBL_5_2.0")
    BBU_5_2_0: float = Field(alias="BBU_5_2.0")
    MACD_12_26_9: float
    MACDs_12_26_9: float

app = FastAPI() 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="template")

model_dir = "./model/model.pkl"
with open(model_dir, mode='rb') as file: 
    model = pickle.load(file)

Instrumentator().instrument(app).expose(app)

conf_gauge = Gauge('prediction_confidence', 'Confidence score of the prediction')
inference_time = Histogram('inference_time_seconds', 'Time spent processing inference')

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/predict")
def predict(data: InputItem):
    start_time = time.time()
    arr = np.array([
        [
            data.Low,
            data.High,
            data.Close,
            data.SMA_10, 
            data.RSI_14, 
            data.ATRr_14, 
            data.ADX_14, 
            data.DMP_14, 
            data.DMN_14, 
            data.SKEW_30, 
            data.SLOPE_1, 
            data.BBL_5_2_0, 
            data.BBU_5_2_0, 
            data.MACD_12_26_9, 
            data.MACDs_12_26_9
        ]
    ])
    pred = model.predict(arr)[0]
    confidence_score = model.predict_proba(arr)[0][pred]
    end_time = time.time()
    inference_time.observe(end_time - start_time)
    conf_gauge.set(confidence_score)
    return {'prediction': int(pred)}

@app.get("/metrics")
def metrics():
    return Response(
        content=prometheus_client.generate_latest(),
        media_type='text/plain'
    )