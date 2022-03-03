import json
import boto3
import logging


def lambda_handler(event, context):
    client = boto3.client('lex-runtime')

    response = client.post_text(
        botName='DiningConciergeChatbot',
        botAlias='Beta',
        userId='lf0',
        inputText=event['messages'][0]['unstructured']['text'])

    return {
        'statusCode': 200,
        'messages': [{
            'type': 'unstructured',
            'unstructured': {
                'text': response['message']
            }
        }]
    }
