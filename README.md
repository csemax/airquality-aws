# Air Quality Monitoring System - Jawa Timur AWS

Sistem monitoring kualitas udara Jawa Timur berbasis AWS. Data diambil dari WAQI API berdasarkan station ID, diproses oleh Lambda, disimpan ke DynamoDB/S3, ditampilkan melalui dashboard EC2 Flask + Leaflet.js, dan diarsipkan ke RDS MySQL.

## Region

`us-east-1`

## Station WAQI

Environment variable `CITIES` untuk Lambda fetcher:

```text
surabaya:@420154,pasuruan:@519130,malang:@13647,kediri:@519187,mojokerto:@519280,jombang:@516745,probolinggo:@532009,banyuwangi:@519112,madiun:@519016,bojonegoro:@519019
```

## Arsitektur

```text
WAQI API → Lambda Fetcher → DynamoDB + S3 + SNS → EC2 Dashboard → Lambda Archiver → RDS MySQL
```

## Lambda Fetcher

Handler: `handler.lambda_handler`

Environment variables:

```text
AWS_REGION=us-east-1
WAQI_TOKEN=isi_token_waqi
CITIES=surabaya:@420154,pasuruan:@519130,malang:@13647,kediri:@519187,mojokerto:@519280,jombang:@516745,probolinggo:@532009,banyuwangi:@519112,madiun:@519016,bojonegoro:@519019
DYNAMODB_TABLE=air_quality_realtime
S3_BUCKET=nama_bucket_s3
SNS_TOPIC_ARN=arn_sns_topic
DASHBOARD_URL=public_ip_ec2
```

## Lambda Archiver

Handler: `lambda_function.lambda_handler`

Environment variables:

```text
AWS_REGION=us-east-1
DYNAMODB_TABLE=air_quality_realtime
DB_HOST=endpoint_rds
DB_USER=admin
DB_PASSWORD=password_rds
DB_NAME=airquality_db
DB_PORT=3306
```

Package archiver:

```bash
cd lambda/archiver
python3 -m pip install --target . -r requirements.txt
zip -r air-quality-archiver.zip .
```

## Dashboard EC2

```bash
cd dashboard
python3 -m pip install --user -r requirements.txt
sudo python3 app.py
```

Atau background:

```bash
sudo gunicorn -w 2 -b 0.0.0.0:80 app:app --daemon
```

## RDS

Jalankan:

```bash
mysql -h endpoint_rds -u admin -p < infrastructure/rds_schema.sql
```
