import requests
import json # for writing category data to file
import logging
import os
import errno
import dicebox.dicebox_config
import dicebox.filesystem_connecter


# Config
config_file = './dicebox.config'
CONFIG = dicebox.docker_config.DockerConfig(config_file)


###############################################################################
# Allows for easy directory structure creation
# https://stackoverflow.com/questions/273192/how-can-i-create-a-directory-if-it-does-not-exist
###############################################################################
def make_sure_path_exists(path):
    try:
        if os.path.exists(path) is False:
            os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


###############################################################################
# Setup logging.
###############################################################################
make_sure_path_exists(CONFIG.LOGS_DIR)
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.DEBUG,
    filemode='w',
    filename="%s/mnist_test_client.%s.log" % (CONFIG.LOGS_DIR, os.uname()[1])
)


def get_category_map():
    jdata = {}
    response = make_api_call('api/category', None, 'GET')
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
        'API-ACCESS-KEY': CONFIG.API_ACCESS_KEY,
        'API-VERSION': CONFIG.API_VERSION
    }
    try:
        url = "%s%s:%i/%s" % (CONFIG.SERVER_URI, CONFIG.CLASSIFICATION_SERVER, CONFIG.SERVER_PORT, end_point)
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
fsc = dicebox.filesystem_connecter.FileSystemConnector(CONFIG.DATA_DIRECTORY, False, config_file)
network_input_index = fsc.get_data_set()
print('Network Input Index: %s' % network_input_index)

# Get our classification categories
server_category_map = get_category_map()
print('Category Map: %s' % server_category_map)

###############################################################################
# Evaluate the Model
###############################################################################

summary_fail = 0
summary_success = 0

count = 0
for item, metadata in network_input_index.iteritems():
    # metadata = network_input_index[item]
    # item = key
    # metadata = value
    print("(%s%s)(%s)" % (CONFIG.DATA_DIRECTORY, item, metadata[1]))

    filename = "%s%s" % (CONFIG.DATA_DIRECTORY, item)
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
        if prediction != -1:
            category = server_category_map[str(prediction)]
        else:
            SERVER_ERROR = True
    else:
        SERVER_ERROR = True

    if SERVER_ERROR is False:
        if category == metadata[1]:
            print('correct!')
            summary_success += 1
        else:
            print('FAIL')
            summary_fail += 1
    else:
        print('SERVER ERROR!')

    if count >= 1999:
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

