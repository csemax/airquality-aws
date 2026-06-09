import os
import boto3
import pymysql
from decimal import Decimal
from datetime import datetime

REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
DB_HOST = os.environ["DB_HOST"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_NAME = os.environ["DB_NAME"]
DB_PORT = int(os.environ.get("DB_PORT", "3306"))

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event, context):
    print("Start archiving DynamoDB to RDS")
    items = scan_dynamodb()
    print(f"Items found: {len(items)}")
    processed = insert_to_rds(items)
    print(f"Rows processed: {processed}")
    return {"statusCode": 200, "items_found": len(items), "rows_processed": processed}


def scan_dynamodb():
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def insert_to_rds(items):
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=10,
    )
    processed = 0
    sql = """
    INSERT IGNORE INTO air_quality_history
    (city, station_name, station_id, recorded_at, aqi, pm25, pm10, o3, no2, so2, co,
     temperature, humidity, category, level, health_message)
    VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        with connection.cursor() as cursor:
            for item in items:
                city = item.get("city")
                timestamp = item.get("timestamp")
                if not city or not timestamp:
                    continue
                cursor.execute(sql, (
                    city,
                    item.get("station_name", "-"),
                    item.get("station_id", "-"),
                    parse_datetime(timestamp),
                    to_float(item.get("aqi")),
                    to_float(item.get("pm25")),
                    to_float(item.get("pm10")),
                    to_float(item.get("o3")),
                    to_float(item.get("no2")),
                    to_float(item.get("so2")),
                    to_float(item.get("co")),
                    to_float(item.get("temperature")),
                    to_float(item.get("humidity")),
                    item.get("category", "Unknown"),
                    int(to_float(item.get("level"))),
                    item.get("health_message", ""),
                ))
                processed += 1
        connection.commit()
    finally:
        connection.close()
    return processed


def to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    if value is None or value == "-":
        return 0
    try:
        return float(value)
    except Exception:
        return 0


def parse_datetime(value):
    if not value:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        return value.replace("T", " ").split(".")[0].replace("+00:00", "")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
