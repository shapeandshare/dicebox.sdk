# this app extracts the mnist data sets for use with dicebox
# mnist data sets from here
# http://yann.lecun.com/exdb/mnist/


from mnist import MNIST
import os
import errno
from PIL import Image


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
# Decode and store ..
###############################################################################
mndata = MNIST('mnist')
image_width = 28
image_height = 28


# training data
# images, labels = mndata.load_training()
# dataset_name = 'training'

# testing data
images, labels = mndata.load_testing()
dataset_name = 'testing'

for i in range(len(images)):
    category = str(labels[i])
    image_data = images[i]

    img = Image.new('RGB', (image_height,image_width))
    pixels = img.load()
    index = 0
    for y in range(image_height):
        for x in range(image_width):
            pixels[x,y] = (image_data[index], image_data[index], image_data[index])
            index += 1

    path = "./mnist/%s/%s/" % (dataset_name, category)
    make_sure_path_exists(path)
    img.save("%s/mnist_%s_%s_%ix%i_%i.png" % (
        path,
        dataset_name,
        category,
        image_width,
        image_height,
        i
    ))
