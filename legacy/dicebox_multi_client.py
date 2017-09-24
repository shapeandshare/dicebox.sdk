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
camera.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 480)

font = cv.CV_FONT_HERSHEY_SIMPLEX

def get_image():
    im = None
    try:
        retval, im = camera.read()
    except:
        print('Unable to read from camera!')

    im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return im


def crop_image(image):
    # Crop Image If Required
    # Now ensure we are the same dimensions as when we started
    cropped_image = None
    #marked_capture = None

    #original_width, original_height = im.size
    original_height, original_width = image.shape[:2]

    new_width = config.IMAGE_WIDTH
    new_height = config.IMAGE_HEIGHT

    new_middle_x = float(new_width) / 2
    new_middle_y = float(new_height) / 2

    left =  int((float(original_width) / 2) - new_middle_x)
    upper = int((float(original_height) / 2)- new_middle_y)
    right = int(new_middle_x + float(original_width) / 2)
    lower = int(new_middle_y + float(original_height) / 2)

    # NOTE: its img[y: y + h, x: x + w] and *not* img[x: x + w, y: y + h]

    width_offset = int(config.IMAGE_WIDTH)

    left_cropped_image = numpy.copy(image[upper:lower, (left - width_offset):(right - width_offset)])
    cropped_image = numpy.copy(image[upper:lower, left:right])
    right_cropped_image = numpy.copy(image[upper:lower, (left + width_offset):(right + width_offset)])

    marked_capture = cv.fromarray(image)

    cv.Rectangle(marked_capture, ((left - width_offset)-1, upper-1), ((right-width_offset)+1,lower+1), (255,0,0), thickness=1, lineType=8, shift=0)
    cv.Rectangle(marked_capture, (left-1, upper-1), (right+1,lower+1), (255,0,0), thickness=1, lineType=8, shift=0)
    cv.Rectangle(marked_capture, ((left+width_offset)-1, upper-1), ((right+width_offset)+1,lower+1), (255,0,0), thickness=1, lineType=8, shift=0)

    return [left_cropped_image, cropped_image, right_cropped_image], marked_capture

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
    cropped_images, marked_capture = crop_image(camera_capture)

    left_filename = datetime.now().strftime('capture_left_%Y-%m-%d_%H_%M_%S_%f.png')
    middle_filename = datetime.now().strftime('capture_middle_%Y-%m-%d_%H_%M_%S_%f.png')
    right_filename = datetime.now().strftime('capture_right_%Y-%m-%d_%H_%M_%S_%f.png')

    left_tmp_file_path = "%s/%s" % (config.TMP_DIR, left_filename)
    middle_tmp_file_path = "%s/%s" % (config.TMP_DIR, middle_filename)
    right_tmp_file_path = "%s/%s" % (config.TMP_DIR, right_filename)

    # A nice feature of the imwrite method is that it will automatically choose the
    # correct format based on the file extension you provide. Convenient!
    left_cropped_image = cropped_images[0]
    cropped_image = cropped_images[1]
    right_cropped_image = cropped_images[2]

    cv2.imwrite(left_tmp_file_path, left_cropped_image)
    with open(left_tmp_file_path, 'rb') as tmp_file:
        left_content = tmp_file.read()


    cv2.imwrite(middle_tmp_file_path, cropped_image)
    with open(middle_tmp_file_path, 'rb') as tmp_file:
        middle_content = tmp_file.read()

    cv2.imwrite(right_tmp_file_path, right_cropped_image)
    with open(right_tmp_file_path, 'rb') as tmp_file:
        right_content = tmp_file.read()


    if KEEP_INPUT:
        if not MISCLASSIFIED_CATEGORY_INDEX and ONLY_KEEP_MISCLASSIFIED_INPUT:
            os.remove(left_tmp_file_path)
            os.remove(middle_tmp_file_path)
            os.remove(right_tmp_file_path)
        else:
            new_path = "%s/%s" % (config.TMP_DIR, server_category_map[str(CURRENT_EXPECTED_CATEGORY_INDEX-1)])
            make_sure_path_exists(new_path)
            new_full_path = "%s/%s" % (new_path, middle_filename)
            os.rename(middle_tmp_file_path, new_full_path)
            os.remove(left_tmp_file_path)
            os.remove(right_tmp_file_path)
    else:
        os.remove(left_tmp_file_path)
        os.remove(middle_tmp_file_path)
        os.remove(right_tmp_file_path)

    base64_encoded_left_content = left_content.encode('base64')
    base64_encoded_middle_content = middle_content.encode('base64')
    base64_encoded_right_content = right_content.encode('base64')

    outbound_content = [base64_encoded_left_content, base64_encoded_middle_content, base64_encoded_right_content]
    categories = []
    category_result = []
    for content in outbound_content:
        outjson = {}
        outjson['data'] = content

        json_data = json.dumps(outjson)

        prediction = {}
        category = {}

        SERVER_ERROR = False
        response = make_api_call('api/classify', json_data, 'POST')
        if 'classification' in response:
            prediction = response['classification']
            if prediction != -1:
                category = server_category_map[str(prediction)]
                categories.append(category)
        else:
            SERVER_ERROR = True

        if category == server_category_map[str(CURRENT_EXPECTED_CATEGORY_INDEX-1)]:
            # MISCLASSIFIED_CATEGORY_INDEX = False
            category_result.append(False)
        else:
            # MISCLASSIFIED_CATEGORY_INDEX = True
            category_result.append(True)

    MISCLASSIFIED_CATEGORY_INDEX = category_result[1]
    cv2.namedWindow('dice box', cv2.WINDOW_NORMAL)

    output_display = camera_capture
    #resized_display = cv2.resize(output_display, (config.IMAGE_WIDTH, config.IMAGE_HEIGHT))
    resized_display = cropped_image

    height, width = output_display.shape[:2]
    output_display[height - config.IMAGE_HEIGHT:height, 0:config.IMAGE_WIDTH] = resized_display  # cv2.cvtColor(resized_display, cv2.COLOR_BGR2GRAY)
    output_display = cv2.cvtColor(output_display, cv2.COLOR_GRAY2RGB)

    output_label_1 = "[expecting %s]" % server_category_map[str(CURRENT_EXPECTED_CATEGORY_INDEX - 1)]
    cv2.putText(output_display, output_label_1, (5, 20), font, 0.7, (255, 255, 255), 2)

    if len(categories) == 3:
        output_label_2 = "[left][classified %s][match? %r]" % (categories[0], not category_result[0])
        output_label_3 = "[middle][classified %s][match? %r]" % (categories[1], not category_result[1])
        output_label_4 = "[right][classified %s][match? %r]" % (categories[2], not category_result[2])
        cv2.putText(output_display, output_label_2, (5, 50), font, 0.7, (255, 255, 255), 2)
        cv2.putText(output_display, output_label_3, (5, 80), font, 0.7, (255, 255, 255), 2)
        cv2.putText(output_display, output_label_4, (5, 110), font, 0.7, (255, 255, 255), 2)

    output_label_5 = "[record? %r][only keep misclassified? %r]" % (KEEP_INPUT, ONLY_KEEP_MISCLASSIFIED_INPUT)
    output_label_6 = "[server error? %r]" % SERVER_ERROR
    cv2.putText(output_display, output_label_5, (5, 140), font, 0.5, (255, 0, 0), 2)
    cv2.putText(output_display, output_label_6, (5, 170), font, 0.5, (0, 255, 255), 0)

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
