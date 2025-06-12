from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pickle
import numpy as np
import time
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

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

# Load model
model_dir = "./model/model.pkl"
with open(model_dir, mode='rb') as file:
    model = pickle.load(file)

# API metrics
REQUEST_COUNT = Counter('request_count_total', 'Total number of requests')
ERROR_COUNT = Counter('error_count_total', 'Total number of errors')
LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds')

# Model metrics
INFERENCE_TIME = Histogram('inference_time_seconds', 'Inference time in seconds')
CONFIDENCE = Gauge('prediction_confidence', 'Confidence score of the prediction')

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    REQUEST_COUNT.inc()
    LATENCY.observe(latency)
    if response.status_code >= 400:
        ERROR_COUNT.inc()
    return response

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
    inference_time = end_time - start_time
    INFERENCE_TIME.observe(inference_time)
    CONFIDENCE.set(confidence_score)
    return {'prediction': int(pred),
            'confidence': float(confidence_score),
            'inference_time': inference_time
            }

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type='text/plain'
    )