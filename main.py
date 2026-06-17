"""
==========================================================
API DỰ BÁO AMONI (TAN) TRONG AO NUÔI TÔM
FastAPI + Random Forest
==========================================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
import joblib
import os



# ----------------------------------------------------------
# KHỞI TẠO APP
# ----------------------------------------------------------

app = FastAPI(
    title="TAN Prediction API",
    description="API dự báo nồng độ Amoni (TAN) trong ao nuôi tôm",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------
# LOAD MODEL & SCALER
# (Đặt file .pkl cùng thư mục với main.py)
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
    print("   API vẫn khởi động nhưng /predict sẽ báo lỗi cho đến khi load được model.")
    model    = None
    scaler_X = None


# ----------------------------------------------------------
# NGƯỠNG CẢNH BÁO AMONI (mg/L)
# Tôm thẻ chân trắng / tôm sú — điều chỉnh theo thực tế
# ----------------------------------------------------------

THRESHOLD_SAFE    = 0.5    # < 0.5 mg/L  → An toàn
THRESHOLD_WARNING = 1.0    # 0.5–1.0     → Cảnh báo
                           # > 1.0       → Nguy hiểm


def classify_tan(value_mg_l: float) -> dict:
    """Phân loại mức độ an toàn dựa trên nồng độ TAN."""
    if value_mg_l < THRESHOLD_SAFE:
        return {
            "level": "AN TOÀN",
            "level_en": "SAFE",
            "color": "green",
            "message": f"TAN = {value_mg_l:.3f} mg/L — Nằm trong ngưỡng an toàn (< {THRESHOLD_SAFE} mg/L).",
            "action": "Không cần can thiệp. Tiếp tục theo dõi định kỳ."
        }
    elif value_mg_l < THRESHOLD_WARNING:
        return {
            "level": "CẢNH BÁO",
            "level_en": "WARNING",
            "color": "orange",
            "message": f"TAN = {value_mg_l:.3f} mg/L — Đang tăng, cần theo dõi chặt ({THRESHOLD_SAFE}–{THRESHOLD_WARNING} mg/L).",
            "action": "Tăng sục khí, giảm lượng thức ăn, kiểm tra pH và nhiệt độ."
        }
    else:
        return {
            "level": "NGUY HIỂM",
            "level_en": "DANGER",
            "color": "red",
            "message": f"TAN = {value_mg_l:.3f} mg/L — Vượt ngưỡng nguy hiểm (> {THRESHOLD_WARNING} mg/L).",
            "action": "Can thiệp ngay: thay nước, tăng sục khí tối đa, ngưng cho ăn, xét dùng vi sinh."
        }


# ----------------------------------------------------------
# SCHEMA ĐẦU VÀO
# Thứ tự features phải KHỚP với selected_features lúc train
# Điều chỉnh danh sách bên dưới theo đúng output của pipeline
# ----------------------------------------------------------

class PredictRequest(BaseModel):
    # --- Lag features ---
    Amoni_lag1: float = Field(..., description="Nồng độ Amoni đo lần trước (mg/L)", example=0.45)
    Amoni_lag2: float = Field(..., description="Nồng độ Amoni đo 2 lần trước (mg/L)", example=0.40)

    # --- Chỉ số nước ---
    Do_kiem:    float = Field(..., description="Độ kiềm (mg/L CaCO3)", example=120.0)
    Tuoi_tom:   float = Field(..., description="Tuổi tôm (ngày)", example=45.0)
    Do_man:     float = Field(..., description="Độ mặn (‰)", example=15.0)
    Do_duc:     float = Field(..., description="Độ đục (NTU)", example=25.0)
    Nhiet_do:   float = Field(..., description="Nhiệt độ (°C)", example=29.5)
    Phosphate:  float = Field(..., description="Phosphate PO4³⁻ (mg/L)", example=0.1)
    pH:         float = Field(..., description="pH", example=7.8)
    DO:         float = Field(..., description="Oxy hòa tan (mg/L)", example=6.2)
    Do_trong:   float = Field(..., description="Độ trong (cm)", example=35.0)
    Silica:     float = Field(..., description="Silica (mg/L)", example=1.5)
    Do_mau:     float = Field(..., description="Độ màu (Pt-Co)", example=10.0)
    Nitrit:     float = Field(..., description="Nitrit NO2- (mg/L)", example=0.02)
    Do_cung:    float = Field(..., description="Độ cứng (mg/L CaCO3)", example=800.0)

    # --- Thức ăn ---
    thucan_lysine:       float = Field(..., description="Lysine (%)", example=1.8)
    thucan_protein_tho:  float = Field(..., description="Protein thô (%)", example=35.0)
    thucan_beo:          float = Field(..., description="Tỉ lệ béo trong thức ăn (%)", example=7.0)
    thucan_xo_tho:       float = Field(..., description="Xơ thô (%)", example=3.5)


# ----------------------------------------------------------
# SCHEMA ĐẦU RA
# ----------------------------------------------------------

class PredictResponse(BaseModel):
    tan_predicted_mg_l:  float
    tan_log_predicted:   float
    warning_level:       str
    warning_level_en:    str
    warning_color:       str
    warning_message:     str
    recommended_action:  str
    input_summary:       dict


# ----------------------------------------------------------
# HELPER: build feature vector theo đúng thứ tự
# ⚠️  Quan trọng: thứ tự này phải KHỚP với selected_features
#     lúc train. Nếu pipeline loại bớt feature nào thì bỏ ở đây.
# ----------------------------------------------------------

# Thứ tự CHÍNH XÁC theo selected_features của pipeline
FEATURE_ORDER = [
    "Amoni_lag1",
    "Do_kiem",
    "Amoni_lag2",
    "Tuoi_tom",
    "Do_man",
    "Do_duc",
    "Nhiet_do",
    "Phosphate",
    "pH",
    "thucan_xo_tho",
    "DO",
    "Do_trong",
    "Silica",
    "Do_mau",
    "Nitrit",
    "Do_cung",
    "thucan_lysine",
    "thucan_protein_tho",
    "thucan_beo",
]


def build_feature_vector(req: PredictRequest) -> np.ndarray:
    data = {
        "Amoni_lag1":           req.Amoni_lag1,
        "Amoni_lag2":           req.Amoni_lag2,
        "Do_kiem":              req.Do_kiem,
        "Tuoi_tom":             req.Tuoi_tom,
        "Do_man":               req.Do_man,
        "Do_duc":               req.Do_duc,
        "Nhiet_do":             req.Nhiet_do,
        "Phosphate":            req.Phosphate,
        "pH":                   req.pH,
        "thucan_xo_tho":        req.thucan_xo_tho,
        "DO":                   req.DO,
        "Do_trong":             req.Do_trong,
        "Silica":               req.Silica,
        "Do_mau":               req.Do_mau,
        "Nitrit":               req.Nitrit,
        "Do_cung":              req.Do_cung,
        "thucan_lysine":        req.thucan_lysine,
        "thucan_protein_tho":   req.thucan_protein_tho,
        "thucan_beo":           req.thucan_beo,
    }
    vector = np.array([data[f] for f in FEATURE_ORDER], dtype=float)
    return vector.reshape(1, -1)


# ----------------------------------------------------------
# ENDPOINTS
# ----------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "running",
        "api": "TAN Prediction API v1.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "model_loaded":  model    is not None,
        "scaler_loaded": scaler_X is not None,
        "model_path":    MODEL_PATH,
        "scaler_path":   SCALER_PATH,
    }


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(req: PredictRequest):
    if model is None or scaler_X is None:
        raise HTTPException(
            status_code=503,
            detail="Model chưa được load. Kiểm tra đường dẫn rf_model.pkl và scaler_X.pkl."
        )

    try:
        # 1. Build feature vector
        X = build_feature_vector(req)

        # 2. Scale
        X_scaled = scaler_X.transform(X)

        # 3. Predict (log scale)
        y_log = float(model.predict(X_scaled)[0])

        # 4. Inverse transform về mg/L
        y_mg_l = float(np.expm1(y_log))
        y_mg_l = max(0.0, y_mg_l)  # không âm

        # 5. Cảnh báo
        warn = classify_tan(y_mg_l)

        return PredictResponse(
            tan_predicted_mg_l  = round(y_mg_l, 4),
            tan_log_predicted   = round(y_log,  4),
            warning_level       = warn["level"],
            warning_level_en    = warn["level_en"],
            warning_color       = warn["color"],
            warning_message     = warn["message"],
            recommended_action  = warn["action"],
            input_summary       = req.model_dump(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/thresholds", tags=["Config"])
def get_thresholds():
    """Xem ngưỡng cảnh báo hiện tại."""
    return {
        "safe_below_mg_l":    THRESHOLD_SAFE,
        "warning_below_mg_l": THRESHOLD_WARNING,
        "danger_above_mg_l":  THRESHOLD_WARNING,
        "unit": "mg/L",
        "note": "Áp dụng cho tôm thẻ chân trắng / tôm sú. Điều chỉnh trong main.py nếu cần."
    }