import boto3
import os
import json
import math
import datetime
import dateutil.parser
import time
import logging


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
SQS = boto3.client("sqs")

""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def getQueueURL():
    """Retrieve the URL for the configured queue name"""
    q = "https://sqs.us-east-1.amazonaws.com/497366965479/Q1"
    return q


def pushMsgToQueue(event):
    """The method to push data to queue"""
    logger.debug("Recieved data from event %s", event)
    data = event.get('data')
    try:
        logger.debug("Pushing data to queue %s", data)
        u = getQueueURL()
        logging.debug("Queue URL: %s", u)
        resp = SQS.send_message(
            QueueUrl=u,
            MessageBody="Dining Prefrences message from LF1 ",
            MessageAttributes={
                "City": {
                    "StringValue": str(get_slots(event)["City"]),
                    "DataType": "String"
                },
                "Cuisine": {
                    "StringValue": str(get_slots(event)["Cuisine"]),
                    "DataType": "String"
                },
                "Date": {
                    "StringValue": get_slots(event)["Date"],
                    "DataType": "String"
                },
                "Time": {
                    "StringValue": str(get_slots(event)["Time"]),
                    "DataType": "String"
                },
                "Number": {
                    "StringValue": str(get_slots(event)["Number"]),
                    "DataType": "String"
                },
                "Mobil": {
                    "StringValue": str(get_slots(event)["Mobil"]),
                    "DataType": "String"
                }
            }
        )
        logger.debug("Pushed messgae to queue, got response: %s", resp)
    except Exception as e:
        raise Exception("Could not recpush msg to queue! %s" % e)


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


""" --- Delegates the response responsibility to bot --- """


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def validate_dining_preferences(city, cuisine, date, time, numPeople, mobil):
    cities = ['manhattan', 'new york', 'brooklyn',
              'jersey city', 'queens', 'bronx']
    if city is not None and city.lower() not in cities:
        return build_validation_result(False,
                                       'City',
                                       'We do not have suggestions for {}, would you like suggestions for a some other location?'.format(city))

    cuisines = ['chinese', 'indian', 'italian', 'japanese', 'american']
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                       'Cuisine',
                                       'We do not have suggestions for {}, would you like suggestions for a differenet cuisine ?  '.format(cuisine))

    if numPeople is not None and not numPeople.isnumeric():
        return build_validation_result(False,
                                       'Number',
                                       'That does not look like a valid number {}, '
                                       'Could you please repeat?'.format(numPeople))

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date', 'I did not understand that, what date would you like to have the recommendation for?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'Date',  'Sorry, that is not possible What day would you like to have the recommendation for?')

    if time is not None:
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', None)
        logger.debug(datetime.datetime.now().hour)
        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', "Can you please specify time?")

        if hour < parse_int(datetime.datetime.now().hour):
            return build_validation_result(False, 'Time', 'Past is history, can you please specify a valid time?')
        elif hour == parse_int(datetime.datetime.now().hour) & minute < parse_int(datetime.datetime.now().minute):
            return build_validation_result(False, 'Time', 'Past is history, can you please specify a valid time?')

        if hour < 10 or hour > 24:
            # Outside of business hours
            return build_validation_result(False, 'Time', 'Our business hours are from 10 AM. to 11 PM. Can you specify a time during this range?')

    if mobil is not None and not mobil.isnumeric():
        return build_validation_result(False,
                                       'Mobil',
                                       'That does not look like a valid number {}, '
                                       'Could you please repeat? '.format(mobil))
    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """


def diningSuggestions(intent_request, context):

    city = get_slots(intent_request)["City"]
    cuisine = get_slots(intent_request)["Cuisine"]
    date = get_slots(intent_request)["Date"]
    time = get_slots(intent_request)["Time"]
    numPeople = get_slots(intent_request)["Number"]
    mobil = get_slots(intent_request)["Mobil"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_dining_preferences(
            city, cuisine, date, time, numPeople, mobil)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Delegate - let the bot to send the final message the user.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
        }
        return delegate(output_session_attributes, get_slots(intent_request))

    # push the message to SQS once all slots are validated
    pushMsgToQueue(intent_request)
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thank you for the information, You’re all set. Expect my suggestions shortly on your phone number! Have a good day.'})


""" --- Intents --- """


def greet(intent_request):
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hey there, Good to see you. How may I serve you today?'})


def thankYou(intent_request):
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'My pleasure, Have a great day!!'})


def dispatch(intent_request, context):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(
        intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return diningSuggestions(intent_request, context)
    elif intent_name == 'ThankYouIntent':
        return thankYou(intent_request)
    elif intent_name == 'GreetingIntent':
        return greet(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event, context)
