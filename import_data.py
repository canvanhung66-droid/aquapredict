"""
Script import dữ liệu từ Excel vào Supabase
Chạy: python import_data.py
"""

import pandas as pd
import httpx
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ──
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Thiếu SUPABASE_URL hoặc SUPABASE_KEY. "
        "Đặt trong file .env hoặc biến môi trường hệ thống."
    )
FILE_PATH    = r"C:\Users\TANDAT\files\Data-chaydulieu2.xlsx"

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation"
}

def post(table, data):
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS, json=data, timeout=30
    )
    r.raise_for_status()
    return r.json()

def safe(val):
    """Chuyển NaN/None về None cho JSON."""
    if val is None: return None
    try:
        import math
        if math.isnan(float(val)): return None
        return float(val)
    except:
        return str(val) if val else None

def safe_int(val):
    try:
        import math
        v = float(val)
        if math.isnan(v): return None
        return int(v)
    except:
        return None

# ── ĐỌC FILE ──
print("📂 Đọc file Excel...")
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip()
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

# Chỉ lấy 4 ao được chọn
SELECTED_PONDS = ['A2D4', 'A2D5', 'A2N9', 'A2N10']
df = df[df['ao'].isin(SELECTED_PONDS)]
print(f"   → {len(df)} dòng, {df['ao'].nunique()} ao: {SELECTED_PONDS}")

# ── TẠO AO ──
print("\n🐟 Tạo ao nuôi trong Supabase...")
pond_map = {}  # ao_name → pond_id

for ao_name in df['ao'].unique():
    ao_df = df[df['ao'] == ao_name].sort_values('Date')
    area  = ao_df['area'].iloc[0] if 'area' in ao_df.columns else None

    try:
        result = post("ponds", {
            "name":          ao_name,
            "area":          str(area) if area and str(area) != 'nan' else None,
            "species":       "Tôm thẻ chân trắng",
            "stocking_date": ao_df['Date'].min().strftime('%Y-%m-%d'),
        })
        pond_id = result[0]['id'] if isinstance(result, list) else result['id']
        pond_map[ao_name] = pond_id
        print(f"   ✅ {ao_name} → {pond_id}")
    except Exception as e:
        print(f"   ⚠️  {ao_name}: {e}")

# ── IMPORT MEASUREMENTS ──
print(f"\n📊 Import {len(df)} bản ghi số liệu...")
success = 0
errors  = 0

for i, row in df.iterrows():
    ao_name = row['ao']
    if ao_name not in pond_map:
        continue

    # Ghép datetime
    try:
        hour = int(row.get('Time', 6)) if row.get('Time') else 6
        dt   = row['Date'].replace(hour=hour)
        dt_str = dt.strftime('%Y-%m-%dT%H:%M:%S')
    except:
        dt_str = row['Date'].strftime('%Y-%m-%dT%H:%M:%S')

    payload = {
        "pond_id":      pond_map[ao_name],
        "measured_at":  dt_str,
        "tan":          safe(row.get('TAN')),
        "ph":           safe(row.get('pH')),
        "do_val":       safe(row.get('DO')),
        "temperature":  safe(row.get('Nhiệt độ')),
        "salinity":     safe(row.get('Độ mặn')),
        "alkalinity":   safe(row.get('Độ kiềm')),
        "hardness":     safe(row.get('Độ cứng')),
        "tds":          safe(row.get('TDS')),
        "turbidity":    safe(row.get('Độ đục')),
        "transparency": safe(row.get('Độ trong')),
        "color":        safe(row.get('Độ màu')),
        "nitrite":      safe(row.get('Nitrit')),
        "nitrate":      safe(row.get('Nitrat')),
        "phosphate":    safe(row.get('Phosphate (PO43-)')),
        "silica":       safe(row.get('Silica')),
        "shrimp_age":   safe_int(row.get('Tuổi tôm')),
    }
    # Bỏ key None
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        post("measurements", payload)
        success += 1
        if success % 50 == 0:
            print(f"   → {success}/{len(df)} dòng...")
        time.sleep(0.05)  # Tránh rate limit
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"   ❌ Dòng {i}: {e}")

print(f"\n✅ Hoàn thành!")
print(f"   Thành công: {success} dòng")
print(f"   Lỗi:        {errors} dòng")
print(f"   Ao đã tạo:  {len(pond_map)} ao")
print("\n🌐 Mở app để xem dữ liệu thật!")
