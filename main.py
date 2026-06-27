"""
==========================================================
API DỰ BÁO AMONI (TAN) TRONG AO NUÔI TÔM
FastAPI + Random Forest + Supabase
==========================================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import numpy as np
import joblib
import os
import httpx
from dotenv import load_dotenv

load_dotenv()


# ----------------------------------------------------------
# KHỞI TẠO APP
# ----------------------------------------------------------

app = FastAPI(
    title="AquaPredict API",
    description="API dự báo TAN và quản lý ao nuôi tôm",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------
# SUPABASE CONFIG
# ----------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Thiếu SUPABASE_URL hoặc SUPABASE_KEY. "
        "Đặt trong file .env hoặc biến môi trường hệ thống."
    )

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


async def supabase_get(table: str, params: dict = {}):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=SUPABASE_HEADERS, params=params)
        if r.status_code not in (200, 206):
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()


async def supabase_post(table: str, data: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=SUPABASE_HEADERS, json=data)
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()


async def supabase_delete(table: str, match: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {k: f"eq.{v}" for k, v in match.items()}
    async with httpx.AsyncClient() as client:
        r = await client.delete(url, headers=SUPABASE_HEADERS, params=params)
        if r.status_code not in (200, 204):
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return {"deleted": True}


# ----------------------------------------------------------
# LOAD MODEL & SCALER
# ----------------------------------------------------------

MODEL_PATH  = os.getenv("MODEL_PATH",  "rf_model.pkl")
SCALER_PATH = os.getenv("SCALER_PATH", "scaler_X.pkl")

try:
    model    = joblib.load(MODEL_PATH)
    scaler_X = joblib.load(SCALER_PATH)
    print(f"✅ Model loaded: {MODEL_PATH}")
    print(f"✅ Scaler loaded: {SCALER_PATH}")
except FileNotFoundError as e:
    print(f"⚠️  WARNING: {e}")
    model    = None
    scaler_X = None


# ----------------------------------------------------------
# NGƯỠNG CẢNH BÁO
# ----------------------------------------------------------

THRESHOLD_SAFE    = 0.5
THRESHOLD_WARNING = 1.0


def classify_tan(value_mg_l: float) -> dict:
    if value_mg_l < THRESHOLD_SAFE:
        return {
            "level": "AN TOÀN", "level_en": "SAFE", "color": "green",
            "message": f"TAN = {value_mg_l:.3f} mg/L — Nằm trong ngưỡng an toàn (< {THRESHOLD_SAFE} mg/L).",
            "action": "Không cần can thiệp. Tiếp tục theo dõi định kỳ."
        }
    elif value_mg_l < THRESHOLD_WARNING:
        return {
            "level": "CẢNH BÁO", "level_en": "WARNING", "color": "orange",
            "message": f"TAN = {value_mg_l:.3f} mg/L — Đang tăng, cần theo dõi chặt.",
            "action": "Tăng sục khí, giảm lượng thức ăn, kiểm tra pH và nhiệt độ."
        }
    else:
        return {
            "level": "NGUY HIỂM", "level_en": "DANGER", "color": "red",
            "message": f"TAN = {value_mg_l:.3f} mg/L — Vượt ngưỡng nguy hiểm (> {THRESHOLD_WARNING} mg/L).",
            "action": "Can thiệp ngay: thay nước, tăng sục khí tối đa, ngưng cho ăn, xét dùng vi sinh."
        }


# ----------------------------------------------------------
# SCHEMAS — PREDICT
# ----------------------------------------------------------

class PredictRequest(BaseModel):
    Amoni_lag1: float = Field(..., example=0.45)
    Amoni_lag2: float = Field(..., example=0.40)
    Do_kiem:    float = Field(..., example=120.0)
    Tuoi_tom:   float = Field(..., example=45.0)
    Do_man:     float = Field(..., example=15.0)
    Do_duc:     float = Field(..., example=25.0)
    Nhiet_do:   float = Field(..., example=29.5)
    Phosphate:  float = Field(..., example=0.1)
    pH:         float = Field(..., example=7.8)
    DO:         float = Field(..., example=6.2)
    Do_trong:   float = Field(..., example=35.0)
    Silica:     float = Field(..., example=1.5)
    Do_mau:     float = Field(..., example=10.0)
    Nitrit:     float = Field(..., example=0.02)
    Do_cung:    float = Field(..., example=800.0)
    thucan_lysine:       float = Field(..., example=1.8)
    thucan_protein_tho:  float = Field(..., example=35.0)
    thucan_beo:          float = Field(..., example=7.0)
    thucan_xo_tho:       float = Field(..., example=3.5)


class PredictResponse(BaseModel):
    tan_predicted_mg_l:  float
    tan_log_predicted:   float
    warning_level:       str
    warning_level_en:    str
    warning_color:       str
    warning_message:     str
    recommended_action:  str
    input_summary:       dict


FEATURE_ORDER = [
    "Amoni_lag1","Do_kiem","Amoni_lag2","Tuoi_tom","Do_man","Do_duc",
    "Nhiet_do","Phosphate","pH","thucan_xo_tho","DO","Do_trong","Silica",
    "Do_mau","Nitrit","Do_cung","thucan_lysine","thucan_protein_tho","thucan_beo",
]


def build_feature_vector(req: PredictRequest) -> np.ndarray:
    data = req.model_dump()
    vector = np.array([data[f] for f in FEATURE_ORDER], dtype=float)
    return vector.reshape(1, -1)


# ----------------------------------------------------------
# SCHEMAS — POND
# ----------------------------------------------------------

class PondCreate(BaseModel):
    name: str = Field(..., example="Ao 05")
    area: Optional[str] = Field(None, example="Khu C")
    size_m2: Optional[float] = None
    pond_type: Optional[str] = None
    species: Optional[str] = None
    stocking_date: Optional[str] = None
    stocking_count: Optional[int] = None
    density: Optional[float] = None
    note: Optional[str] = None


# ----------------------------------------------------------
# SCHEMAS — MEASUREMENT
# ----------------------------------------------------------

class MeasurementCreate(BaseModel):
    pond_id: str
    measured_at: Optional[str] = None
    tan: Optional[float] = None
    ph: Optional[float] = None
    do_val: Optional[float] = None
    temperature: Optional[float] = None
    salinity: Optional[float] = None
    alkalinity: Optional[float] = None
    hardness: Optional[float] = None
    tds: Optional[float] = None
    turbidity: Optional[float] = None
    transparency: Optional[float] = None
    color: Optional[float] = None
    nitrite: Optional[float] = None
    nitrate: Optional[float] = None
    phosphate: Optional[float] = None
    silica: Optional[float] = None
    shrimp_age: Optional[int] = None
    note: Optional[str] = None


# ----------------------------------------------------------
# ENDPOINTS — HEALTH
# ----------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {"status": "running", "api": "AquaPredict API v2.0", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health():
    return {
        "model_loaded":  model    is not None,
        "scaler_loaded": scaler_X is not None,
        "supabase_url":  SUPABASE_URL,
    }


# ----------------------------------------------------------
# ENDPOINTS — PREDICT
# ----------------------------------------------------------

@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(req: PredictRequest):
    if model is None or scaler_X is None:
        raise HTTPException(status_code=503, detail="Model chưa được load.")
    try:
        X        = build_feature_vector(req)
        X_scaled = scaler_X.transform(X)
        y_log    = float(model.predict(X_scaled)[0])
        y_mg_l   = max(0.0, float(np.expm1(y_log)))
        warn     = classify_tan(y_mg_l)
        return PredictResponse(
            tan_predicted_mg_l = round(y_mg_l, 4),
            tan_log_predicted  = round(y_log,  4),
            warning_level      = warn["level"],
            warning_level_en   = warn["level_en"],
            warning_color      = warn["color"],
            warning_message    = warn["message"],
            recommended_action = warn["action"],
            input_summary      = req.model_dump(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------
# ENDPOINTS — PONDS
# ----------------------------------------------------------

@app.get("/ponds", tags=["Ponds"])
async def get_ponds():
    """Lấy danh sách tất cả ao nuôi."""
    return await supabase_get("ponds", {"order": "created_at.desc"})


@app.post("/ponds", tags=["Ponds"])
async def create_pond(pond: PondCreate):
    """Tạo ao nuôi mới."""
    data = {k: v for k, v in pond.model_dump().items() if v is not None}
    result = await supabase_post("ponds", data)
    return result[0] if isinstance(result, list) else result


@app.delete("/ponds/{pond_id}", tags=["Ponds"])
async def delete_pond(pond_id: str):
    """Xoá ao nuôi."""
    return await supabase_delete("ponds", {"id": pond_id})


# ----------------------------------------------------------
# ENDPOINTS — MEASUREMENTS
# ----------------------------------------------------------

@app.get("/measurements", tags=["Measurements"])
async def get_measurements(pond_id: Optional[str] = None, limit: int = 100):
    """Lấy lịch sử số liệu. Lọc theo pond_id nếu có."""
    params = {"order": "measured_at.desc", "limit": str(limit)}
    if pond_id:
        params["pond_id"] = f"eq.{pond_id}"
    return await supabase_get("measurements", params)


@app.post("/measurements", tags=["Measurements"])
async def create_measurement(m: MeasurementCreate):
    """Nhập số liệu đo hàng ngày cho một ao."""
    data = {k: v for k, v in m.model_dump().items() if v is not None}
    result = await supabase_post("measurements", data)
    return result[0] if isinstance(result, list) else result


@app.delete("/measurements/{measurement_id}", tags=["Measurements"])
async def delete_measurement(measurement_id: str):
    """Xoá một bản ghi số liệu."""
    return await supabase_delete("measurements", {"id": measurement_id})


# ----------------------------------------------------------
# ENDPOINTS — DASHBOARD
# ----------------------------------------------------------

@app.get("/dashboard/{pond_id}", tags=["Dashboard"])
async def get_dashboard(pond_id: str):
    """
    Lấy dữ liệu dashboard cho một ao:
    - 7 bản ghi mới nhất để vẽ biểu đồ
    - Bản ghi mới nhất để hiển thị stat card
    """
    params = {
        "pond_id": f"eq.{pond_id}",
        "order": "measured_at.desc",
        "limit": "7"
    }
    records = await supabase_get("measurements", params)

    if not records:
        return {"latest": None, "chart_data": [], "pond_id": pond_id}

    latest   = records[0]
    chart    = list(reversed(records))   # sắp xếp tăng dần để vẽ biểu đồ

    return {
        "pond_id":    pond_id,
        "latest":     latest,
        "chart_data": chart,
    }


@app.get("/thresholds", tags=["Config"])
def get_thresholds():
    return {
        "safe_below_mg_l":    THRESHOLD_SAFE,
        "warning_below_mg_l": THRESHOLD_WARNING,
        "danger_above_mg_l":  THRESHOLD_WARNING,
        "unit": "mg/L"
    }
