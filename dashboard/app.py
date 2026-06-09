from flask import Flask, render_template, jsonify
import boto3
from decimal import Decimal
from datetime import datetime

app = Flask(__name__)
REGION = "us-east-1"
TABLE_NAME = "air_quality_realtime"
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

ALLOWED_CITIES = {"surabaya", "pasuruan", "malang", "kediri", "mojokerto", "jombang", "probolinggo", "banyuwangi", "madiun", "bojonegoro"}
DEFAULT_COORDINATES = {
    "surabaya": {"lat": -7.24917, "lon": 112.75083},
    "pasuruan": {"lat": -7.64530, "lon": 112.90750},
    "malang": {"lat": -7.96662, "lon": 112.63263},
    "kediri": {"lat": -7.81660, "lon": 112.01160},
    "mojokerto": {"lat": -7.46640, "lon": 112.43380},
    "jombang": {"lat": -7.54595, "lon": 112.23307},
    "probolinggo": {"lat": -7.75430, "lon": 113.21590},
    "banyuwangi": {"lat": -8.21920, "lon": 114.36910},
    "madiun": {"lat": -7.62980, "lon": 111.52390},
    "bojonegoro": {"lat": -7.15020, "lon": 111.88170},
}
DISPLAY_NAMES = {
    "surabaya": "Kota Surabaya", "pasuruan": "Kota Pasuruan", "malang": "Kota Malang", "kediri": "Kota Kediri",
    "mojokerto": "Kota Mojokerto", "jombang": "Kabupaten Jombang", "probolinggo": "Kota Probolinggo",
    "banyuwangi": "Kabupaten Banyuwangi", "madiun": "Kota Madiun", "bojonegoro": "Kabupaten Bojonegoro",
}

def convert_decimal(obj):
    if isinstance(obj, list): return [convert_decimal(i) for i in obj]
    if isinstance(obj, dict): return {k: convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal): return float(obj)
    return obj

def get_marker_color(category):
    return {"Good":"green", "Moderate":"gold", "Unhealthy (Sens)":"orange", "Unhealthy":"red", "Very Unhealthy":"purple", "Hazardous":"maroon"}.get(category, "blue")

def safe_float(value):
    try:
        if value is None or value == "-": return 0
        return float(value)
    except Exception:
        return 0

def normalize_city_name(city):
    return str(city).strip().lower() if city else ""

def get_latest_all_cities():
    try:
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        latest = {}
        for item in items:
            city = normalize_city_name(item.get("city"))
            timestamp = item.get("timestamp", "")
            if city not in ALLOWED_CITIES: continue
            if city not in latest or timestamp > latest[city].get("timestamp", ""):
                latest[city] = item
        cities = convert_decimal(list(latest.values()))
        for city in cities:
            name = normalize_city_name(city.get("city"))
            city["city"] = name
            city["display_name"] = DISPLAY_NAMES.get(name, name.title())
            if "lat" not in city or "lon" not in city or city.get("lat") in [None, 0] or city.get("lon") in [None, 0]:
                coord = DEFAULT_COORDINATES.get(name)
                if coord:
                    city["lat"] = coord["lat"]
                    city["lon"] = coord["lon"]
            for key in ["aqi", "pm25", "pm10", "temperature", "humidity", "o3", "no2", "so2", "co"]:
                city[key] = safe_float(city.get(key))
            city["category"] = city.get("category", "Unknown")
            city["color"] = city.get("color", "#2563eb")
            city["marker_color"] = get_marker_color(city.get("category"))
            city["station_name"] = city.get("station_name", "-")
            city["station_id"] = city.get("station_id", "-")
            city["health_message"] = city.get("health_message", "Informasi kesehatan belum tersedia.")
        cities.sort(key=lambda x: x.get("aqi", 0), reverse=True)
        return cities
    except Exception as e:
        print(f"ERROR DynamoDB: {e}")
        return []

def get_dashboard_summary(cities):
    if not cities:
        return {"total_cities": 0, "highest_aqi": "-", "worst_city": "-", "average_aqi": "-"}
    highest = max(cities, key=lambda x: x.get("aqi", 0))
    avg = sum(c.get("aqi", 0) for c in cities) / len(cities)
    return {"total_cities": len(cities), "highest_aqi": round(highest.get("aqi", 0)), "worst_city": highest.get("display_name", "-"), "average_aqi": round(avg, 1)}

@app.route("/")
def index():
    cities = get_latest_all_cities()
    return render_template("index.html", cities=cities, summary=get_dashboard_summary(cities))

@app.route("/api/cities")
def api_cities():
    return jsonify(get_latest_all_cities())

@app.route("/api/summary")
def api_summary():
    cities = get_latest_all_cities()
    return jsonify(get_dashboard_summary(cities))

@app.route("/health")
def health():
    return {"status": "ok", "service": "airquality-dashboard", "region": REGION, "table": TABLE_NAME, "time": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
