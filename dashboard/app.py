from flask import Flask, render_template, jsonify
import boto3
import pymysql
from decimal import Decimal
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

REGION = "us-east-1"
TABLE_NAME = "air_quality_realtime"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# =========================
# KONFIGURASI RDS MYSQL
# =========================
DB_HOST = "airquality-mysql.cwuofoo15ikw.us-east-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "ISI_PASSWORD_RDS_KAMU"
DB_NAME = "airquality_db"
DB_PORT = 3306


ALLOWED_CITIES = {
    "surabaya",
    "pasuruan",
    "malang",
    "kediri",
    "mojokerto",
    "jombang",
    "probolinggo",
    "banyuwangi",
    "madiun",
    "bojonegoro"
}


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
    "bojonegoro": {"lat": -7.15020, "lon": 111.88170}
}


DISPLAY_NAMES = {
    "surabaya": "Kota Surabaya",
    "pasuruan": "Kota Pasuruan",
    "malang": "Kota Malang",
    "kediri": "Kota Kediri",
    "mojokerto": "Kota Mojokerto",
    "jombang": "Kabupaten Jombang",
    "probolinggo": "Kota Probolinggo",
    "banyuwangi": "Kabupaten Banyuwangi",
    "madiun": "Kota Madiun",
    "bojonegoro": "Kabupaten Bojonegoro"
}


def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]

    if isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}

    if isinstance(obj, Decimal):
        return float(obj)

    return obj


def get_marker_color(category):
    colors = {
        "Good": "green",
        "Moderate": "gold",
        "Unhealthy (Sens)": "orange",
        "Unhealthy": "red",
        "Very Unhealthy": "purple",
        "Hazardous": "maroon"
    }

    return colors.get(category, "blue")


def normalize_city_name(city):
    if not city:
        return ""

    return str(city).strip().lower()


def safe_float(value):
    try:
        if value is None or value == "-":
            return 0

        return float(value)

    except Exception:
        return 0


def parse_iso_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    except Exception:
        return None


def get_relative_time(timestamp):
    dt = parse_iso_datetime(timestamp)

    if not dt:
        return "-"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = int(diff.total_seconds())

    if seconds < 0:
        seconds = 0

    if seconds < 60:
        return f"{seconds} detik lalu"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes} menit lalu"

    hours = minutes // 60

    if hours < 24:
        return f"{hours} jam lalu"

    days = hours // 24

    return f"{days} hari lalu"


def format_datetime_display(timestamp):
    dt = parse_iso_datetime(timestamp)

    if not dt:
        return "-"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    WIB = timezone(timedelta(hours=7))
    wib = dt.astimezone(WIB)

    return wib.strftime("%Y-%m-%d %H:%M:%S WIB")


def get_latest_all_cities():
    try:
        response = table.scan()
        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            response = table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        latest = {}

        for item in items:
            city = normalize_city_name(item.get("city"))
            timestamp = item.get("timestamp", "")

            if city not in ALLOWED_CITIES:
                continue

            if city not in latest:
                latest[city] = item

            elif timestamp > latest[city].get("timestamp", ""):
                latest[city] = item

        cities = convert_decimal(list(latest.values()))

        for city in cities:
            name = normalize_city_name(city.get("city"))

            city["city"] = name
            city["display_name"] = DISPLAY_NAMES.get(name, name.title())

            if (
                "lat" not in city
                or "lon" not in city
                or city.get("lat") in [None, 0]
                or city.get("lon") in [None, 0]
            ):
                coord = DEFAULT_COORDINATES.get(name)

                if coord:
                    city["lat"] = coord["lat"]
                    city["lon"] = coord["lon"]

            city["aqi"] = safe_float(city.get("aqi"))
            city["pm25"] = safe_float(city.get("pm25"))
            city["pm10"] = safe_float(city.get("pm10"))
            city["temperature"] = safe_float(city.get("temperature"))
            city["humidity"] = safe_float(city.get("humidity"))
            city["o3"] = safe_float(city.get("o3"))
            city["no2"] = safe_float(city.get("no2"))
            city["so2"] = safe_float(city.get("so2"))
            city["co"] = safe_float(city.get("co"))

            city["category"] = city.get("category", "Unknown")
            city["color"] = city.get("color", "#2563eb")
            city["marker_color"] = get_marker_color(city.get("category"))
            city["station_name"] = city.get("station_name", "-")
            city["station_id"] = city.get("station_id", "-")
            city["health_message"] = city.get(
                "health_message",
                "Informasi kesehatan belum tersedia."
            )

            city["relative_time"] = get_relative_time(city.get("timestamp", ""))
            city["formatted_time"] = format_datetime_display(city.get("timestamp", ""))

        cities.sort(key=lambda x: x.get("aqi", 0), reverse=True)

        return cities

    except Exception as e:
        print(f"ERROR DynamoDB: {e}")
        return []


def get_dashboard_summary(cities):
    if not cities:
        return {
            "total_cities": 0,
            "highest_aqi": "-",
            "worst_city": "-",
            "last_taken": "-",
            "last_taken_detail": "-"
        }

    total = len(cities)
    highest = max(cities, key=lambda x: x.get("aqi", 0))

    latest_city = max(
        cities,
        key=lambda x: x.get("timestamp", "")
    )

    latest_timestamp = latest_city.get("timestamp", "")

    return {
        "total_cities": total,
        "highest_aqi": round(highest.get("aqi", 0)),
        "worst_city": highest.get("display_name", "-"),
        "last_taken": get_relative_time(latest_timestamp),
        "last_taken_detail": format_datetime_display(latest_timestamp)
    }


def get_aqi_trend_from_rds(hours=24):
    """
    Mengambil data historis AQI dari RDS MySQL
    untuk ditampilkan sebagai grafik tren di dashboard.
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )

        sql = """
        SELECT
            city,
            recorded_at,
            aqi
        FROM air_quality_history
        WHERE recorded_at >= NOW() - INTERVAL %s HOUR
        ORDER BY recorded_at ASC
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, (hours,))
            rows = cursor.fetchall()

        connection.close()

        trend = {}

        WIB = timezone(timedelta(hours=7))

        for row in rows:
            city = normalize_city_name(row.get("city"))
            recorded_at = row.get("recorded_at")
            aqi = row.get("aqi")

            if city not in ALLOWED_CITIES:
                continue

            if city not in trend:
                trend[city] = {
                    "labels": [],
                    "data": []
                }

            if isinstance(recorded_at, datetime):
                recorded_at = recorded_at.replace(tzinfo=timezone.utc)
                recorded_at_wib = recorded_at.astimezone(WIB)
                label = recorded_at_wib.strftime("%H:%M")
            else:
                label = str(recorded_at)

            trend[city]["labels"].append(label)
            trend[city]["data"].append(float(aqi) if aqi is not None else 0)

        return trend

    except Exception as e:
        print(f"ERROR RDS Trend: {e}")
        return {}


@app.route("/")
def index():
    cities = get_latest_all_cities()
    summary = get_dashboard_summary(cities)
    aqi_trend = get_aqi_trend_from_rds(hours=24)

    return render_template(
        "index.html",
        cities=cities,
        summary=summary,
        aqi_trend=aqi_trend
    )


@app.route("/api/cities")
def api_cities():
    return jsonify(get_latest_all_cities())


@app.route("/api/summary")
def api_summary():
    cities = get_latest_all_cities()
    return jsonify(get_dashboard_summary(cities))


@app.route("/api/rds/trend")
def api_rds_trend():
    return jsonify(get_aqi_trend_from_rds(hours=24))


@app.route("/health")
def health():
    return {
        "status": "ok",
        "service": "airquality-dashboard",
        "region": REGION,
        "table": TABLE_NAME,
        "time": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
