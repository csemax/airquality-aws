import os
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
sns = boto3.client("sns", region_name=REGION)


def send_alert(data: dict):
    topic_arn = os.environ.get("SNS_TOPIC_ARN")
    if not topic_arn:
        print("SNS_TOPIC_ARN belum di-set. Alert dilewati.")
        return

    subject = f"[{data['category'].upper()}] Kualitas Udara {data['city'].title()}"
    message = f"""
PERINGATAN KUALITAS UDARA

Kota      : {data['city'].title()}
Station   : {data.get('station_name', '-')}
Station ID: {data.get('station_id', '-')}
Status    : {data['category']}
AQI       : {data['aqi']}
PM2.5     : {data['pm25']} µg/m³ ({data.get('pm25_category', '-')})
PM10      : {data['pm10']} µg/m³
Waktu     : {data['classified_at']}

{data['health_message']}

Polutan dominan: {data.get('dominant_pollutant', 'N/A').upper()}
Dashboard: http://{os.environ.get('DASHBOARD_URL', 'localhost')}
"""
    sns.publish(TopicArn=topic_arn, Subject=subject[:100], Message=message)
