from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import pickle
import numpy as np
import time
import logging
import logging.handlers
import sys
import traceback
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# ----- Logging setup for 3 streams -----
# 1. STDOUT Logger - for normal application logs
stdout_logger = logging.getLogger("app.stdout")
stdout_logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
stdout_handler.setFormatter(stdout_formatter)
stdout_logger.addHandler(stdout_handler)
stdout_logger.propagate = False

# 2. STDERR Logger - for errors and tracebacks
stderr_logger = logging.getLogger("app.stderr")
stderr_logger.setLevel(logging.ERROR)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
stderr_handler.setFormatter(stderr_formatter)
stderr_logger.addHandler(stderr_handler)
stderr_logger.propagate = False

# 3. SYSLOG Logger - for system-level events
syslog_logger = logging.getLogger("app.syslog")
syslog_logger.setLevel(logging.WARNING)
try:
    # Send to Fluentd syslog input
    syslog_handler = logging.handlers.SysLogHandler(address=('fluentd', 5140))
    syslog_formatter = logging.Formatter("fastapi[%(process)d]: %(levelname)s - %(message)s")
    syslog_handler.setFormatter(syslog_formatter)
    syslog_logger.addHandler(syslog_handler)
    syslog_logger.propagate = False
    stdout_logger.info("Syslog handler configured successfully")
except Exception as e:
    stdout_logger.warning(f"Could not create syslog handler: {e}")

# ----- FastAPI -----
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="template")

# ----- Load model -----
model_dir = "./model/model.pkl"
try:
    with open(model_dir, mode='rb') as file:
        model = pickle.load(file)
    stdout_logger.info(f"Model loaded successfully from {model_dir}")
    syslog_logger.info(f"FastAPI model loaded: {model_dir}")
except Exception as e:
    stderr_logger.error(f"Failed to load model from {model_dir}: {e}")
    stderr_logger.error(f"Traceback: {traceback.format_exc()}")
    syslog_logger.error(f"Critical: Model loading failed - {e}")
    raise

# ----- Prometheus metrics -----
REQUEST_COUNT = Counter('request_count_total', 'Total number of requests')
ERROR_COUNT = Counter('error_count_total', 'Total number of errors')
LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds')
INFERENCE_TIME = Histogram('inference_time_seconds', 'Inference time in seconds')
CONFIDENCE = Gauge('prediction_confidence', 'Confidence score of the prediction')

# ----- Input schema -----
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

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        response = await call_next(request)
        latency = time.time() - start_time
        
        # STDOUT: Normal request logging
        stdout_logger.info(f"Request completed | {request.method} {request.url.path} | "
                          f"Status: {response.status_code} | Latency: {latency:.4f}s | Client: {client_ip}")
        
        REQUEST_COUNT.inc()
        LATENCY.observe(latency)
        
        if response.status_code >= 400:
            ERROR_COUNT.inc()
            # STDERR: HTTP errors
            stderr_logger.error(f"HTTP Error | {request.method} {request.url.path} | "
                              f"Status: {response.status_code} | Client: {client_ip}")
            # SYSLOG: System-level HTTP error notification
            syslog_logger.warning(f"HTTP {response.status_code} error on {request.url.path} from {client_ip}")
            
        return response
        
    except Exception as e:
        latency = time.time() - start_time
        
        # STDERR: Unhandled exceptions with full traceback
        stderr_logger.error(f"Unhandled exception | {request.method} {request.url.path} | "
                           f"Error: {str(e)} | Latency: {latency:.4f}s | Client: {client_ip}")
        stderr_logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # SYSLOG: Critical system notification
        syslog_logger.error(f"Critical: Unhandled exception in FastAPI - {str(e)}")
        
        ERROR_COUNT.inc()
        raise

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    stdout_logger.info("Root endpoint accessed")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/predict")
def predict(data: InputItem):
    start_time = time.time()
    
    # Validate input data
    try:
        arr = np.array([[
            data.Low, data.High, data.Close, data.SMA_10, data.RSI_14, data.ATRr_14, data.ADX_14,
            data.DMP_14, data.DMN_14, data.SKEW_30, data.SLOPE_1, data.BBL_5_2_0,
            data.BBU_5_2_0, data.MACD_12_26_9, data.MACDs_12_26_9
        ]])
        
        # Check for invalid values
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            raise ValueError("Input contains NaN or infinite values")
            
    except Exception as e:
        # STDERR: Input validation errors with details
        stderr_logger.error(f"Input validation failed: {str(e)} | Input: {data.dict()}")
        stderr_logger.error(f"Validation traceback: {traceback.format_exc()}")
        ERROR_COUNT.inc()
        raise HTTPException(status_code=400, detail="Invalid input data")
    
    try:
        pred = model.predict(arr)[0]
        confidence_score = model.predict_proba(arr)[0][pred]
        
        inference_time = time.time() - start_time
        INFERENCE_TIME.observe(inference_time)
        CONFIDENCE.set(confidence_score)

        # STDOUT: Successful prediction logging
        stdout_logger.info(f"Prediction successful | Prediction: {pred} | "
                          f"Confidence: {confidence_score:.4f} | Time: {inference_time:.4f}s")

        return {
            'prediction': int(pred),
            'confidence': float(confidence_score),
            'inference_time': inference_time
        }
        
    except Exception as e:
        inference_time = time.time() - start_time
        
        # STDERR: Prediction failures with full traceback
        stderr_logger.error(f"Prediction failed | Error: {str(e)} | Time: {inference_time:.4f}s")
        stderr_logger.error(f"Prediction traceback: {traceback.format_exc()}")
        stderr_logger.error(f"Input data: {data.dict()}")
        
        # SYSLOG: Critical prediction system failure
        syslog_logger.error(f"Critical: ML prediction system failure - {str(e)}")
        
        ERROR_COUNT.inc()
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.get("/metrics")
def metrics():
    stdout_logger.info("Metrics endpoint accessed")
    return Response(
        content=generate_latest(),
        media_type='text/plain'
    )

# Application startup logging
stdout_logger.info("FastAPI application starting up")
stdout_logger.info(f"Model loaded from: {model_dir}")
stdout_logger.info("Logging configured: stdout (info), stderr (errors), syslog (warnings+)")
syslog_logger.info("FastAPI application started successfully")