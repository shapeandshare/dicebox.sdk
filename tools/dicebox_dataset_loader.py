import requests
from dicebox import dicebox_config as config  # import our high level configuration
from dicebox import filesystem_connecter # inport our file system connector for input
import json # for writing category data to file
import os

def get_category_map():
    jdata = {}
    with open('./docs/category_map.json') as data_file:
        raw_cat_data = json.load(data_file)
    for d in raw_cat_data:
        jdata[str(raw_cat_data[d])] = str(d)
    return jdata


def make_api_call(end_point, json_data, call_type):
    headers = {
        'Content-type': 'application/json',
        'API-ACCESS-KEY': config.API_ACCESS_KEY,
        'API-VERSION': config.API_VERSION
    }
    # print(headers)
    url = "%s%s:%i/%s" % (config.SENSORY_URI, config.SENSORY_SERVER, int(config.SENSORY_PORT), end_point)
    try:
        response = None
        # print(url)

        if call_type == 'GET':
            response = requests.get(url, data=json_data, headers=headers)
        elif call_type == 'POST':
            response = requests.post(url, data=json_data, headers=headers)

        if response is not None:
            if response.status_code != 500:
                return response.json()
    except:
        return {}
    return {}


###############################################################################
# prep our data sets
###############################################################################
fsc = filesystem_connecter.FileSystemConnector(config.DATA_DIRECTORY)
network_input_index = fsc.get_data_set()

# Get our classification categories
server_category_map = get_category_map()

for item in network_input_index:
    metadata = network_input_index[item]
    print("(%s%s)(%s)" % (config.DATA_DIRECTORY, item, metadata[1]))

    filename = "%s%s" % (config.DATA_DIRECTORY, item)
    try:
        with open(filename, 'rb') as file:
            file_content = file.read()
    except:
        # if this failed, then we can assume the content has been
        #picked up by another worker and then removed..
        print('failed to ready file contents..')
        break

    base64_encoded_content = file_content.encode('base64')

    outjson = {}
    outjson['data'] = base64_encoded_content
    outjson['name'] = config.DATASET
    outjson['width'] = config.IMAGE_WIDTH
    outjson['height'] = config.IMAGE_HEIGHT
    outjson['category'] = metadata[1]

    json_data = json.dumps(outjson)

    SERVER_ERROR = True

    #print(json_data)
    while SERVER_ERROR is True:
        response = make_api_call('api/sensory/store', json_data, 'POST')
        if 'sensory_store' in response:
            SERVER_ERROR = False
            if response['sensory_store'] is not True:
                print(response['sensory_store'])
            print("transmitted (%s), removing it.." % filename)
            #os.remove(filename)
        else:
            SERVER_ERROR = True
            print('server error, retrying ..')
            print(response)
