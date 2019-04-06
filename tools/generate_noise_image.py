import dicebox.dicebox_config as config
from datetime import datetime
import numpy
from PIL import Image
width = config.IMAGE_WIDTH
height = config.IMAGE_HEIGHT


def generate_random_static_grayscale_image():
    filename = datetime.now().strftime('random_%Y-%m-%d_%H_%M_%S_%f.png')
    tmp_file_path = "%s/%s" % (config.TMP_DIR, filename)
    imarray = numpy.random.rand(width,height,3) * 255
    im = Image.fromarray(imarray.astype('uint8')).convert('L')
    im.save(tmp_file_path)

count = 10000

for i in range(1, count):
    generate_random_static_grayscale_image()
