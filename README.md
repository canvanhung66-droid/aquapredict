# API Dự Báo Amoni (TAN) — Ao Nuôi Tôm

FastAPI + Random Forest · Python 3.9+

---

## 1. Cài đặt

```bash
pip install fastapi uvicorn scikit-learn joblib numpy pandas openpyxl
```

---

## 2. Lưu model và scaler sau khi train

Thêm 2 dòng này vào cuối pipeline train của bạn:

```python
import joblib

joblib.dump(rf_model,  "rf_model.pkl")
joblib.dump(scaler_X,  "scaler_X.pkl")
```

Đặt 2 file `.pkl` **cùng thư mục** với `main.py`.

---

## 3. Điều chỉnh thứ tự features (quan trọng)

Mở `main.py`, tìm biến `FEATURE_ORDER` và sửa cho **khớp hoàn toàn**
với `selected_features` mà pipeline in ra:

```python
FEATURE_ORDER = [
    "Amoni_lag1", "Amoni_lag2",
    "Nitrit", "Nitrat",
    ...  # ← sửa theo đúng output của pipeline
]
```

---

## 4. Chạy API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập tài liệu tự động: **http://localhost:8000/docs**

---

## 5. Gọi API — ví dụ

### curl

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Amoni_lag1": 0.45,
    "Amoni_lag2": 0.40,
    "Nitrit": 0.02,
    "Nitrat": 5.0,
    "pH": 7.8,
    "Nhiet_do": 29.5,
    "DO": 6.2,
    "Do_man": 15.0,
    "TDS": 20000.0,
    "Do_duc": 25.0,
    "Do_mau": 10.0,
    "Do_trong": 35.0,
    "Do_kiem": 120.0,
    "Do_cung": 800.0,
    "Phosphate": 0.1,
    "Silica": 1.5,
    "thucan_beo": 7.0,
    "thucan_lysine": 1.8,
    "thucan_protein_tho": 35.0,
    "thucan_xo_tho": 3.5,
    "Tuoi_tom": 45
  }'
```

### Python

```python
import requests

payload = {
    "Amoni_lag1": 0.45,
    "Amoni_lag2": 0.40,
    "Nitrit": 0.02,
    "Nitrat": 5.0,
    "pH": 7.8,
    "Nhiet_do": 29.5,
    "DO": 6.2,
    "Do_man": 15.0,
    "TDS": 20000,
    "Do_duc": 25.0,
    "Do_mau": 10.0,
    "Do_trong": 35.0,
    "Do_kiem": 120.0,
    "Do_cung": 800.0,
    "Phosphate": 0.1,
    "Silica": 1.5,
    "thucan_beo": 7.0,
    "thucan_lysine": 1.8,
    "thucan_protein_tho": 35.0,
    "thucan_xo_tho": 3.5,
    "Tuoi_tom": 45,
}

r = requests.post("http://localhost:8000/predict", json=payload)
print(r.json())
```

---

## 6. Ví dụ response

```json
{
  "tan_predicted_mg_l": 0.382,
  "tan_log_predicted": 0.323,
  "warning_level": "AN TOÀN",
  "warning_level_en": "SAFE",
  "warning_color": "green",
  "warning_message": "TAN = 0.382 mg/L — Nằm trong ngưỡng an toàn (< 0.5 mg/L).",
  "recommended_action": "Không cần can thiệp. Tiếp tục theo dõi định kỳ.",
  "input_summary": { "..." }
}
```

---

## 7. Các endpoint

| Method | Endpoint      | Mô tả                        |
|--------|---------------|------------------------------|
| GET    | `/`           | Health check                 |
| GET    | `/health`     | Kiểm tra model đã load chưa  |
| POST   | `/predict`    | Dự báo TAN + cảnh báo        |
| GET    | `/thresholds` | Xem ngưỡng cảnh báo          |
| GET    | `/docs`       | Swagger UI tự động           |

---

## 8. Ngưỡng cảnh báo

| Mức        | Nồng độ TAN   | Màu    |
|------------|---------------|--------|
| An toàn    | < 0.5 mg/L    | Xanh   |
| Cảnh báo   | 0.5–1.0 mg/L  | Cam    |
| Nguy hiểm  | > 1.0 mg/L    | Đỏ     |

Chỉnh ngưỡng tại `THRESHOLD_SAFE` và `THRESHOLD_WARNING` trong `main.py`.
