import json
import os
import time
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

    return {"statusCode": 200, "body": json.dumps(results, default=str)}


def fetch_air_quality_by_station(city: str, station_id: str):
    url = f"https://api.waqi.info/feed/{station_id}/?token={TOKEN}"

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
        "raw": payload,
    }


def safe_number(value):
    try:
        if value is None or value == "-":
            return 0
        return float(value)
    except Exception:
        return 0


def save_to_dynamodb(data: dict):
    item = dict(data)
    item.pop("raw", None)
    ttl_time = datetime.now(timezone.utc) + timedelta(days=7)
    item["ttl"] = int(ttl_time.timestamp())
    item = convert_float_to_decimal(item)
    table.put_item(Item=item)


def save_to_s3(city: str, data: dict):
    now = datetime.now(timezone.utc)
    key = f"raw/{city}/{now.year}/{now.month:02d}/{now.day:02d}/{int(time.time())}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(data, default=str),
        ContentType="application/json",
    )


def convert_float_to_decimal(obj):
    if isinstance(obj, list):
        return [convert_float_to_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj
