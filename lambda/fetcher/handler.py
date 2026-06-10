import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3

from classifier import classify_aqi
from notifier import send_alert

REGION = os.environ.get("AWS_REGION", "us-east-1")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

CITIES = os.environ["CITIES"].split(",")
TOKEN = os.environ["WAQI_TOKEN"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
S3_BUCKET = os.environ["S3_BUCKET"]

table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event, context):
    """
    Lambda utama:
    1. Mengambil data kualitas udara dari WAQI API berdasarkan station ID.
    2. Melakukan parsing dan normalisasi data.
    3. Melakukan klasifikasi kualitas udara.
    4. Menyimpan data terstruktur ke DynamoDB.
    5. Menyimpan raw JSON ke S3.
    6. Mengirim notifikasi SNS jika kualitas udara tidak sehat.
    """
    results = []

    for city_config in CITIES:
        city_config = city_config.strip()

        try:
            city, station_id = city_config.split(":")
            city = city.lower().strip()
            station_id = station_id.strip()

            data = fetch_air_quality_by_station(city, station_id)

            if not data:
                print(f"No data for {city}")
                continue

            classified = classify_aqi(data)

            save_to_dynamodb(classified)
            save_to_s3(city, classified)

            if classified["category"] in ["Unhealthy", "Very Unhealthy", "Hazardous"]:
                send_alert(classified)

            results.append(classified)

        except Exception as e:
            print(f"Error processing {city_config}: {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps(results, default=str)
    }


def fetch_air_quality_by_station(city: str, station_id: str):
    """
    Mengambil data WAQI berdasarkan station ID.

    Contoh station ID:
    surabaya:@420154
    pasuruan:@519130
    malang:@13647
    kediri:@519187
    """
    url = f"https://api.waqi.info/feed/{station_id}/?token={TOKEN}"

    print(f"Fetching {city} from {url}")

    with urllib.request.urlopen(url, timeout=10) as response:
        body = response.read().decode("utf-8")

    payload = json.loads(body)

    if payload.get("status") != "ok":
        print(f"WAQI error for {city}: {payload}")
        return None

    data = payload.get("data", {})
    iaqi = data.get("iaqi", {})
    city_info = data.get("city", {})
    geo = city_info.get("geo", [0, 0])

    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "city": city,
        "timestamp": timestamp,
        "aqi": safe_number(data.get("aqi")),
        "pm25": safe_number(iaqi.get("pm25", {}).get("v")),
        "pm10": safe_number(iaqi.get("pm10", {}).get("v")),
        "o3": safe_number(iaqi.get("o3", {}).get("v")),
        "no2": safe_number(iaqi.get("no2", {}).get("v")),
        "so2": safe_number(iaqi.get("so2", {}).get("v")),
        "co": safe_number(iaqi.get("co", {}).get("v")),
        "temperature": safe_number(iaqi.get("t", {}).get("v")),
        "humidity": safe_number(iaqi.get("h", {}).get("v")),
        "dominant_pollutant": data.get("dominentpol", "pm25"),
        "station_name": city_info.get("name", city),
        "station_id": station_id,
        "lat": safe_number(geo[0]) if len(geo) > 0 else 0,
        "lon": safe_number(geo[1]) if len(geo) > 1 else 0,
        "raw": payload
    }


def safe_number(value):
    """
    Mengubah nilai kosong/null menjadi 0.
    """
    try:
        if value is None or value == "-":
            return 0

        return float(value)

    except Exception:
        return 0


def save_to_dynamodb(data: dict):
    """
    Menyimpan data yang sudah diproses ke DynamoDB.

    Data di DynamoDB digunakan untuk:
    - dashboard real-time
    - sumber data Lambda archiver ke RDS
    """
    item = dict(data)

    # Raw response tidak dimasukkan ke DynamoDB agar item tetap ringan.
    item.pop("raw", None)

    # TTL 7 hari agar data real-time tidak menumpuk terlalu banyak.
    ttl_time = datetime.now(timezone.utc) + timedelta(days=7)
    item["ttl"] = int(ttl_time.timestamp())

    item = convert_float_to_decimal(item)

    table.put_item(Item=item)

    print(f"Saved processed data to DynamoDB: {data['city']}")


def save_to_s3(city: str, data: dict):
    """
    Menyimpan raw data ke S3 dengan nama file waktu Indonesia.

    Format file:
    raw/kota/YY-MM-DD_HH-mm-ss_WIB.json

    Contoh:
    raw/kediri/26-06-10_21-35-08_WIB.json
    """

    WIB = timezone(timedelta(hours=7))
    now = datetime.now(WIB)

    filename = now.strftime("%Y-%m-%d_%H-%M-%S_WIB.json")

    key = f"raw/{city}/{filename}"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(data, default=str),
        ContentType="application/json"
    )

    print(f"Saved raw data to s3://{S3_BUCKET}/{key}")


def convert_float_to_decimal(obj):
    """
    DynamoDB boto3 tidak menerima tipe float.
    Float harus dikonversi ke Decimal.
    """
    if isinstance(obj, list):
        return [convert_float_to_decimal(i) for i in obj]

    if isinstance(obj, dict):
        return {k: convert_float_to_decimal(v) for k, v in obj.items()}

    if isinstance(obj, float):
        return Decimal(str(obj))

    return obj
