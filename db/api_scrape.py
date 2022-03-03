from __future__ import print_function

import argparse
import requests
import sys
import csv
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.parse import urlencode


API_KEY = 'sP0K7LZHQ1uL0Ww96owe6RYpvmgNfslowrAbCC1hfFe6iBsVhCSMkV4PvPS-DG0CwS8dEfedjoxL26IuK0GEdglIQ7_6MHSvuHnPJ8ohA7-E9-64uHvJkg9Gz6IdYnYx'

API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/search'
BUSINESS_PATH = '/v3/businesses/'

DEFAULT_TERM = 'Indian restaurants'
DEFAULT_LOCATION = 'Manhattan'
SEARCH_LIMIT = 50
OFFSET = 1000


def request(host, path, api_key, url_params=None):
    url_params = url_params or {}
    url = '{0}{1}'.format(host, quote(path.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % api_key,
    }
    print(u'Querying {0} ...'.format(url))
    response = requests.request('GET', url, headers=headers, params=url_params)
    return response.json()


def search(api_key, term, location, offSet):

    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'offset': offSet,
        'limit': SEARCH_LIMIT
    }
    return request(API_HOST, SEARCH_PATH, api_key, url_params=url_params)


def getTotal(api_key, term, location):

    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'limit': SEARCH_LIMIT
    }
    return request(API_HOST, SEARCH_PATH, api_key, url_params=url_params).get('total')


def get_business(api_key, business_id):
    business_path = BUSINESS_PATH + business_id
    return request(API_HOST, business_path, api_key)


def query_api(term, location):
    dataEntry = []
    dataEntry.append("bID")
    dataEntry.append("name")
    dataEntry.append("address")
    dataEntry.append("cord")
    dataEntry.append("numOfReview")
    dataEntry.append("rating")
    dataEntry.append("zipcode")
    dataEntry.append("cuisine")
    filename = "Restaurants" + '.csv'
    with open(filename, "a", newline='') as fp:
        wr = csv.writer(fp, dialect='excel')
        wr.writerow(dataEntry)

    cuisines = ['chinese', 'indian', 'italian', 'japanese', 'american']
    for cuisine in cuisines:
        newterm = cuisine + ' restaurants'
        total = getTotal(API_KEY, newterm, location)
        print(total, cuisine)
        run = 0
        maxOffSet = int(total / 50)
        businesses = []
        for offSet in range(0, maxOffSet+1):
            if run == 25:
                break
            response = search(API_KEY, newterm, location, offSet*50)
            if response.get('businesses') is None:
                break
            businesses.append(response.get('businesses'))
            run += 1

        printVar = []
        for buis in businesses:
            for b in buis:
                printVar.append(b)

        if not businesses:
            # print(u'No businesses for {0} in {1} found.'.format(term, location))
            return

        for b in printVar:
            bID = b['id']
            name = b['name']
            add = ', '.join(b['location']['display_address'])
            numOfReview = int(b['review_count'])
            rating = float(b['rating'])

            if (b['coordinates'] and b['coordinates']['latitude'] and b['coordinates']['longitude']):
                cord = str(b['coordinates']['latitude']) + ', ' + \
                    str(b['coordinates']['longitude'])
            else:
                cord = None

            if (b['location']['zip_code']):
                zipcode = b['location']['zip_code']
            else:
                zipcode = None

            temparr = []
            temparr.append(bID)
            temparr.append(name)
            temparr.append(add)
            temparr.append(cord)
            temparr.append(numOfReview)
            temparr.append(rating)
            temparr.append(zipcode)
            temparr.append(cuisine)

            with open(filename, "a", newline='') as fp:
                wr = csv.writer(fp, dialect='excel')
                wr.writerow(temparr)

        print("Added ", cuisine, " restaurants")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-q', '--term', dest='term', default=DEFAULT_TERM,
                        type=str, help='Search term (default: %(default)s)')
    parser.add_argument('-l', '--location', dest='location',
                        default=DEFAULT_LOCATION, type=str,
                        help='Search location (default: %(default)s)')

    input_values = parser.parse_args()

    try:
        query_api(input_values.term, input_values.location)
    except HTTPError as error:
        sys.exit(
            'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                error.code,
                error.url,
                error.read(),
            )
        )


if __name__ == '__main__':
    main()
