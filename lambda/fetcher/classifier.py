from datetime import datetime, timezone


def classify_aqi(data: dict) -> dict:
    aqi = int(float(data.get("aqi", 0) or 0))

    if aqi <= 50:
        cat, color, level = "Good", "#00E400", 1
    elif aqi <= 100:
        cat, color, level = "Moderate", "#FFFF00", 2
    elif aqi <= 150:
        cat, color, level = "Unhealthy (Sens)", "#FF7E00", 3
    elif aqi <= 200:
        cat, color, level = "Unhealthy", "#FF0000", 4
    elif aqi <= 300:
        cat, color, level = "Very Unhealthy", "#8F3F97", 5
    else:
        cat, color, level = "Hazardous", "#7E0023", 6

    pm25 = float(data.get("pm25", 0) or 0)
    if pm25 <= 5:
        pm25_cat = "Safe"
    elif pm25 <= 15:
        pm25_cat = "Moderate"
    elif pm25 <= 25:
        pm25_cat = "Elevated"
    elif pm25 <= 50:
        pm25_cat = "High"
    else:
        pm25_cat = "Hazardous"

    return {
        **data,
        "category": cat,
        "color": color,
        "level": level,
        "pm25_category": pm25_cat,
        "health_message": generate_health_message(cat),
        "classified_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_health_message(category: str) -> str:
    messages = {
        "Good": "Kualitas udara baik. Aman untuk aktivitas luar ruangan.",
        "Moderate": "Kualitas udara cukup baik. Orang sangat sensitif sebaiknya kurangi aktivitas berat.",
        "Unhealthy (Sens)": "Tidak sehat untuk kelompok sensitif. Lansia, anak-anak, penderita asma hindari luar ruangan.",
        "Unhealthy": "Tidak sehat untuk semua orang. Kurangi aktivitas luar ruangan.",
        "Very Unhealthy": "Sangat tidak sehat. Hindari semua aktivitas luar ruangan.",
        "Hazardous": "BERBAHAYA. Tetap di dalam ruangan, tutup semua ventilasi.",
    }
    return messages.get(category, "Data tidak tersedia.")
