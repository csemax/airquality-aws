import boto3

REGION = "us-east-1"
TABLE_NAME = "air_quality_realtime"
dynamodb = boto3.client("dynamodb", region_name=REGION)

def create_table():
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "city", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "city", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print("Table creation requested.")
    except dynamodb.exceptions.ResourceInUseException:
        print(f"Table {TABLE_NAME} already exists.")

if __name__ == "__main__":
    create_table()
