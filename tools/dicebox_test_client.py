import requests
from dicebox import dicebox_config as config  # import our high level configuration
from dicebox import filesystem_connecter # inport our file system connector for input
import json # for writing category data to file

def get_category_map():
    jdata = {}
    response = make_api_call('api/categories', None, 'GET')
    if 'category_map' in response:
        jdata = response['category_map']
        print('loaded category map from server.')

    if len(jdata) == 0:
        with open('./category_map.json') as data_file:
            raw_cat_data = json.load(data_file)
        for d in raw_cat_data:
            jdata[str(raw_cat_data[d])] = str(d)
        print('loaded category map from file.')

    # print(jdata)
    return jdata


def make_api_call(end_point, json_data, call_type):
    headers = {
        'Content-type': 'application/json',
        'API-ACCESS-KEY': config.API_ACCESS_KEY,
        'API-VERSION': config.API_VERSION
    }
    try:
        url = "%s%s:%i/%s" % (config.SERVER_URI, config.CLASSIFICATION_SERVER, config.SERVER_PORT, end_point)
        response = None
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

###############################################################################
# Evaluate the Model
###############################################################################

summary_fail = 0
summary_success = 0

count = 0
for item in network_input_index:
    metadata = network_input_index[item]
    print("(%s%s)(%s)" % (config.DATA_DIRECTORY, item, metadata[1]))

    filename = "%s%s" % (config.DATA_DIRECTORY, item)
    with open(filename, 'rb') as file:
        file_content = file.read()

    base64_encoded_content = file_content.encode('base64')

    outjson = {}
    outjson['data'] = base64_encoded_content

    json_data = json.dumps(outjson)

    prediction = {}

    SERVER_ERROR = False
    response = make_api_call('api/classify', json_data, 'POST')
    if 'classification' in response:
        prediction = response['classification']
        category = server_category_map[str(prediction)]
    else:
        SERVER_ERROR = True

    if category == metadata[1]:
        print('correct!')
        summary_success += 1
    else:
        print('FAIL')
        summary_fail += 1

    if count >= 0:
        count += 1
        break
    else:
        count += 1

success_percentage = (float(summary_success) / count) * 100
failure_percentage = (float(summary_fail) / count) * 100

print('summary')
print("success: (%i)" % summary_success)
print("failures: (%i)" % summary_fail)
print("total tests: (%i)" % count)
print("success rate: (%f)" % success_percentage)
print("failure rate: (%f)" % failure_percentage)

