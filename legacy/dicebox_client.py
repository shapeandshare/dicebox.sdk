###############################################################################
# dice box
###############################################################################
import cv
import cv2
from datetime import datetime
import json
import requests
import os
import numpy
import math
from lib import dicebox_config as config  # import our high level configuration
# from PIL import Image
# import sys
import os
import errno

# https://stackoverflow.com/questions/273192/how-can-i-create-a-directory-if-it-does-not-exist
def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

###############################################################################
# configure our camera, and begin our capture and prediction loop
###############################################################################
# Camera 0 is the integrated web cam on my netbook
camera_port = 0

# Number of frames to throw away while the camera adjusts to light levels
ramp_frames = 3

# Now we can initialize the camera capture object with the cv2.VideoCapture class.
# All it needs is the index to a camera port.

camera = cv2.VideoCapture(camera_port)
camera.set(cv.CV_CAP_PROP_FRAME_WIDTH, 1024)
camera.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 768)

font = cv.CV_FONT_HERSHEY_SIMPLEX

def get_image():
    im = None
    try:
        retval, im = camera.read()
    except:
        print('Unable to read from camera!')

    im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return im


def crop_image(im):
    # Crop Image If Required
    # Now ensure we are the same dimensions as when we started
    cropped_image = None
    marked_capture = None

    #original_width, original_height = im.size
    original_height, original_width = im.shape[:2]

    new_width = config.IMAGE_WIDTH
    new_height = config.IMAGE_HEIGHT

    new_middle_x = float(new_width) / 2
    new_middle_y = float(new_height) / 2

    left =  int((float(original_width) / 2) - new_middle_x)
    upper = int((float(original_height) / 2)- new_middle_y)
    right = int(new_middle_x + float(original_width) / 2)
    lower = int(new_middle_y + float(original_height) / 2)

    # NOTE: its img[y: y + h, x: x + w] and *not* img[x: x + w, y: y + h]

    cropped_image = im[upper:lower, left:right]
    #cropped_im = im.crop((left, upper, right, lower))
    #im = im.resize((config.IMAGE_WIDTH, config.IMAGE_HEIGHT), Image.ANTIALIAS)
    #cropped_im = cv2.cvtColor(cropped_im, cv2.COLOR_BGR2GRAY)

    marked_capture = cv.Rectangle(cv.fromarray(im), (left-1, upper-1), (right+1,lower+1), (255,0,0), thickness=1, lineType=8, shift=0)

    return cropped_image, marked_capture

def resize_keep_aspect_ratio(input_image, desired_size):
    height, width = input_image.shape[:2]

    height = float(height)
    width = float(width)

    if width >= height:
        max_dim = width
    else:
        max_dim = height

    scale = float(desired_size) / max_dim

    if width >= height:
        new_width = desired_size
        x = 0
        new_height = height * scale
        y = (desired_size - new_height) / 2
    else:
        y = 0
        new_height = desired_size
        new_width = width * scale
        x = (desired_size - new_width) / 2

    new_height = int(math.floor(new_height))
    new_width = int((math.floor(new_width)))

    resized_input = cv2.resize(input_image, (new_width, new_height))

    output = numpy.zeros((desired_size, desired_size), numpy.uint8)

    x_offset = int(math.floor(x+new_width))
    y_offset = int(math.floor(y+new_height))

    # new lets drop the resized imput onto the output
    output[int(y):int(y_offset), int(x):int(x_offset)] = resized_input

    return output


def get_category_map():
    jdata = {}

    if len(jdata) == 0:
        with open('./category_map.json') as data_file:
            raw_cat_data = json.load(data_file)
        for d in raw_cat_data:
            jdata[str(raw_cat_data[d])] = str(d)
        print('loaded category map from file.')

    if len(jdata) == 0:
        response = make_api_call('api/categories', None, 'GET')
        if 'category_map' in response:
            jdata = response['category_map']
            print('loaded category map from server.')

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


# Ramp the camera - these frames will be discarded and are only used to allow v4l2
# to adjust light levels, if necessary
for i in xrange(ramp_frames):
    temp = get_image()


# Get our classification categories
server_category_map = get_category_map()


# Setup our default state
global CURRENT_EXPECTED_CATEGORY_INDEX
CURRENT_EXPECTED_CATEGORY_INDEX = 11

MAX_EXPECTED_CATEGORY_INDEX = len(server_category_map)

global MISCLASSIFIED_CATEGORY_INDEX
MISCLASSIFIED_CATEGORY_INDEX = True

global KEEP_INPUT
KEEP_INPUT = False

global ONLY_KEEP_MISCLASSIFIED_INPUT
ONLY_KEEP_MISCLASSIFIED_INPUT = True

global SERVER_ERROR
SERVER_ERROR = False



###############################################################################
# main loop
###############################################################################
while True:
    # Take the actual image we want to keep
    # camera_capture, resized_image  = get_image()
    camera_capture = get_image()
    cropped_image, marked_capture = crop_image(camera_capture)
    filename = datetime.now().strftime('capture_%Y-%m-%d_%H_%M_%S_%f.png')
    tmp_file_path = "%s/%s" % (config.TMP_DIR, filename)

    # A nice feature of the imwrite method is that it will automatically choose the
    # correct format based on the file extension you provide. Convenient!
    cv2.imwrite(tmp_file_path, cropped_image)

    with open(tmp_file_path, 'rb') as tmp_file:
        file_content = tmp_file.read()

    if KEEP_INPUT:
        if not MISCLASSIFIED_CATEGORY_INDEX and ONLY_KEEP_MISCLASSIFIED_INPUT:
            os.remove(tmp_file_path)
        else:
            new_path = "%s/%s" % (config.TMP_DIR, server_category_map[str(CURRENT_EXPECTED_CATEGORY_INDEX-1)])
            make_sure_path_exists(new_path)
            new_full_path = "%s/%s" % (new_path, filename)
            os.rename(tmp_file_path, new_full_path)
    else:
        os.remove(tmp_file_path)

    base64_encoded_content = file_content.encode('base64')

    outjson = {}
    outjson['data'] = base64_encoded_content

    json_data = json.dumps(outjson)

    prediction = {}
    category = {}

    SERVER_ERROR = False
    response = make_api_call('api/classify', json_data, 'POST')
    if 'classification' in response:
        prediction = response['classification']
        category = server_category_map[str(prediction)]
    else:
        SERVER_ERROR = True

    if category == server_category_map[str(CURRENT_EXPECTED_CATEGORY_INDEX-1)]:
        MISCLASSIFIED_CATEGORY_INDEX = False
    else:
        MISCLASSIFIED_CATEGORY_INDEX = True

    cv2.namedWindow('dice box', cv2.WINDOW_NORMAL)

    output_display = camera_capture
    #resized_display = cv2.resize(output_display, (config.IMAGE_WIDTH, config.IMAGE_HEIGHT))
    resized_display = cropped_image

    height, width = output_display.shape[:2]
    output_display[height - config.IMAGE_HEIGHT:height, 0:config.IMAGE_WIDTH] = resized_display  # cv2.cvtColor(resized_display, cv2.COLOR_BGR2GRAY)
    output_display = cv2.cvtColor(output_display, cv2.COLOR_GRAY2RGB)

    output_label_1 = "[classified %s/expected %s][match? %r]" % (category, server_category_map[str(CURRENT_EXPECTED_CATEGORY_INDEX-1)], not MISCLASSIFIED_CATEGORY_INDEX)
    output_label_2 = "[record? %r][only keep misclassified? %r]" % (KEEP_INPUT, ONLY_KEEP_MISCLASSIFIED_INPUT)
    output_label_3 = "[server error? %r]" % SERVER_ERROR

    cv2.putText(output_display, output_label_1, (5, 20), font, 0.7, (255, 255, 255), 2)
    cv2.putText(output_display, output_label_2, (5, 50), font, 0.7, (255, 0, 0), 2)
    cv2.putText(output_display, output_label_3, (5, 80), font, 0.5, (0, 255, 255), 0)

    try:
        cv2.imshow('dice box', output_display)
    except:
        print("Unable to display output!")

    input_key = cv2.waitKey(1)

    if input_key & 0xFF == ord('q'):
        break

    if input_key & 0xFF == ord('c'):
        KEEP_INPUT = False
        if CURRENT_EXPECTED_CATEGORY_INDEX >= MAX_EXPECTED_CATEGORY_INDEX:
            CURRENT_EXPECTED_CATEGORY_INDEX = 1
        else:
            CURRENT_EXPECTED_CATEGORY_INDEX += 1

    if input_key & 0xFF == ord('z'):
        if KEEP_INPUT is True:
            KEEP_INPUT = False
        else:
            KEEP_INPUT = True

    if input_key & 0xFF == ord('b'):
            if ONLY_KEEP_MISCLASSIFIED_INPUT is True:
                ONLY_KEEP_MISCLASSIFIED_INPUT = False
            else:
                ONLY_KEEP_MISCLASSIFIED_INPUT = True

###############################################################################
# cleanup
###############################################################################
# You'll want to release the camera, otherwise you won't be able to create a new
# capture object until your script exits
camera.release()
cv2.destroyAllWindows()
