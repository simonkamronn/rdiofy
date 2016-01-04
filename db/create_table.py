from __future__ import print_function # Python 2/3 compatibility
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', endpoint_url="http://localhost:8000")


table = dynamodb.create_table(
    TableName='audio_matches',
    KeySchema=[
        {
            'AttributeName': 'match_id',
            'KeyType': 'HASH'  #Partition key
        },
        {
            'AttributeName': 'recording_time',
            'KeyType': 'RANGE'  #Sort key
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'match_id',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'recording_time',
            'AttributeType': 'S'
        },

    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
    }
)

print("Table status:", table.table_status)
