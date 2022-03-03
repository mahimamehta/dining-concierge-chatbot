import boto3
import json
import logging
from boto3.dynamodb.conditions import Key, Attr
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def getSQSMsg():
    SQS = boto3.client("sqs")
    url = 'https://sqs.us-east-1.amazonaws.com/497366965479/Q1'
    response = SQS.receive_message(
        QueueUrl=url,
        AttributeNames=['SentTimestamp'],
        MessageAttributeNames=['All'],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    try:
        message = response['Messages'][0]
        if message is None:
            logger.debug("Empty message")
            return None
    except KeyError:
        logger.debug("No message in the queue")
        return None
    message = response['Messages'][0]
    SQS.delete_message(
        QueueUrl=url,
        ReceiptHandle=message['ReceiptHandle']
    )
    logger.debug('Received and deleted message: %s' % response)
    return message


def lambda_handler(event, context):
    """
        Query SQS to get the messages
        Store the relevant info, and pass it to the Elastic Search
    """

    message = getSQSMsg()  # data will be a json object
    if message is None:
        logger.debug("No Cuisine or Mobil key found in message")
        return
    cuisine = message["MessageAttributes"]["Cuisine"]["StringValue"]
    location = message["MessageAttributes"]["City"]["StringValue"]
    date = message["MessageAttributes"]["Date"]["StringValue"]
    time = message["MessageAttributes"]["Time"]["StringValue"]
    numOfPeople = message["MessageAttributes"]["Number"]["StringValue"]
    phoneNumber = message["MessageAttributes"]["Mobil"]["StringValue"]
    phoneNumber = "+1" + phoneNumber
    # cuisine = 'indian'
    # location = 'manhattan'
    # date = '2022-03-03'
    # time = '18:00'
    # numOfPeople = 2
    # phoneNumber = '2029678622'
    # phoneNumber = "+1" + phoneNumber
    if not cuisine or not phoneNumber:
        logger.debug("No Cuisine or PhoneNum key found in message")
        return

    """
        Query database based on elastic search results
        Store the relevant info, create the message and sns the info
    """

    es_query = "https://search-diningchatbotdomain-47jvytqd3j74affqad7vr4fhnu.us-east-1.es.amazonaws.com/_search?q={cuisine}".format(
        cuisine=cuisine)
    esResponse = requests.get(es_query, auth=("Demo-ES1", "Demo-ES1"))
    logger.debug(esResponse)
    data = json.loads(esResponse.content.decode('utf-8'))
    try:
        esData = data["hits"]["hits"]
    except KeyError:
        logger.debug("Error extracting hits from ES response")

    # extract bID from AWS ES
    ids = []
    for restaurant in esData:
        ids.append(restaurant["_source"]["bID"])

    messageToSend = 'Hello! Here are my {cuisine} restaurant suggestions in {location} for {numPeople} people, for {diningDate} at {diningTime}: '.format(
        cuisine=cuisine,
        location=location,
        numPeople=numOfPeople,
        diningDate=date,
        diningTime=time,
    )

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    itr = 1
    for id in ids:
        if itr == 6:
            break
        response = table.scan(FilterExpression=Attr('bID').eq(id))
        item = response['Items'][0]
        if response is None:
            continue
        restaurantMsg = '' + str(itr) + '. '
        name = item["name"]
        address = item["address"]
        restaurantMsg += name + ', located at ' + address + '. '
        messageToSend += restaurantMsg
        itr += 1

    messageToSend += "Enjoy your meal!!"

    try:
        client = boto3.client('sns', region_name='us-east-1')
        response = client.publish(
            PhoneNumber=phoneNumber,
            Message=messageToSend,
            MessageStructure='string'
        )
    except KeyError:
        logger.debug("Error sending ")
    logger.debug("response - %s", json.dumps(response))
    logger.debug("Message = '%s' Phone Number = %s" %
                 (messageToSend, phoneNumber))

    return {
        'statusCode': 200,
        'body': json.dumps("LF2 running succesfully")
    }
    # return messageToSend
