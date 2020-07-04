# Dicebox SDK
               Let's shake things up!

Overview
--------
An image classification and training system built with SOA (Service-Oriented Architecture) in mind.  The project includes several client implementations, and future enhancements will continue to expand the API capabilities.

1. **Visual Image Classification**

    Dicebox is a visual classification system.  It can be reconfigured for different image sizes and categories.

2. **Evolutionary Neural Network**

    Dicebox is capable of being applied to a large variety of classification problems.  Sometimes unique or novel problems need to be solved and a neural network structure is unknown.  In this case dicebox provides a means to evolve a network tailored to the particular problem.

3. **Service-Oriented Architecture**
   
*   The trained neural network is accessed through a REST API.  
*   The Web Client (and supervised trainer) stores data to an AWS EFS via the REST API.
*   The Trainer uses the REST API for training data



High Level Components
---------------------

![Dicebox Services Diagram](https://github.com/shapeandshare/dicebox.sdk/raw/master/assets/Dicebox%20Services%20Diagram.png)

* **Client**

    There are several client implementations included with dicebox.
    * [webcam](https://github.com/shapeandshare/dicebox.sdk/tree/master/webcam) is the recommend client for most use cases.  It is a simple html5/css/javascript client and supervised training program.
    * dicebox_test_client.py - meant for bulk image classification and trained network validation.
    * (_legacy_) dicebox_client.py - a python opencv thick client and supervised training program
    * (_legacy_) dicebox_multi_client.py - like the dicebox_client.py but classifies several portions of the screen.

* **Lonestar Trainer**

    The stand-alone training application for a selected network genotype.  It will generate weights files for use by the dicebox service.
    
* **Classification Service**
    
    A REST API that performs classification using the designated network structure and weights.
    
* **Sensory Service**

    The sensory service is a REST API that will store data that needs to be added to training set for a given classification.  It is primary consumed by the stand-alone trainer.

    Provides input data directly for small batch sizes, or can queue up large batch orders for creation by the batch processor.
 
* **Sensory Batch Processor**

    A back-end service for batch order processing.  Will take requests from the message queue, and then create a corresponding queue with data for a consumer.

* **Training Service**

    The training service is a REST API used to request training.

* **Training Processor Service**

    A back-end service for picking up a training request, and performing the training.


Requirements
------------

**Python Module Requirements**

The requirements can be automatically installed using the below command:
```
    pip install -r requirements.txt
```

Configuration
=============
`dicebox.config` contains the configurable parameters for dicebox.

The below section controls the parameters for the network input.
```
[DATASET]
    name = dicebox
    image_width = 100
    image_height = 100
    categories = 19
```

Images are expected to be in the below directory structure.
```
(dataset_base_directory)\
    (name)_(width)x(height)\
        data\
            (category_1)\
            (category_2)\
            [..]
```

The genotypes for the networks (individuals) are defined below; and can be changed. :)
```
[TAXONOMY]
    neurons: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597]
    layers: [1, 2, 3, 5, 8, 13, 21]
    activation: ["softmax", "elu", "softplus", "softsign", "relu", "tanh", "sigmoid", "hard_sigmoid", "linear"]
    optimizer: ["rmsprop", "adam", "sgd", "adagrad", "adadelta", "adamax", "nadam"]
```

Individual networks can be defined and trained.  This controls the network that is trained and used by the service.
```
[LONESTAR]
    neurons = 987
    layers = 5
    activation = elu
    optimizer = adamax
```

The number of epochs, individuals, and generations used during evolution are defined a below.
```
[EVOLUTION]
    epochs = 10000
    generations = 100
    population = 50
```

When training the lonestar network, the below options control the training regiment.
```
[TRAINING]
    batch_size = 15000
    train_batch_size = 223000
    test_batch_size = 15000
    load_best_weights_on_start = False
```

Defines the directories used for the various file system operations.
```
[DIRECTORY]
    dataset_base_directory = datasets
    logs_dir = ./logs
    weights_dir = ./weights
    tmp_dir = ./tmp
```

Controls the service configuration.
```
[SERVER]
    api_access_key = 6e249b5f-b483-4e0d-b50b-81d95e3d9a59
    api_version = 0.3.0
    listening_host = 0.0.0.0
    flask_debug = False
    model_weights_filename = weights.best.hdf5
```

Controls the sernsory service configuration.
```
[SENSORY_SERVICE]
    sensory_server = localhost
    sensory_port = 5000
    sensory_uri = http://
    rabbitmq_exchange = sensory.exchange
    rabbitmq_batch_request_routing_key = task_queue
    rabbitmq_batch_request_task_queue = sensory.batch.request.task.queue
    rabbitmq_uri = amqp://
    rabbitmq_username = guest
    rabbitmq_password = guest
    rabbitmq_server = localhost
    rabbitmq_port = 5672
    rabbitmq_vhost = sensory
```

The percentage of noise/luck in the system. (0 - 1) scale
```
[GLOBAL]
    noise = 0.5
```

Service configuration for the dicebox client.
```
[CLIENT]
    classification_server = localhost
    classification_port = 5000
    classification_uri = http://
```

The Primordial Pool
===================
Based on the defined hyper-parameters evolutionary optimization is employed to select for successive generations of neural networks.  

```
    python ./primordialpool.py
```

Lonestar Training
=================
Allows for the saving of specific networks pulled from the pool.  The trained weights will be saved for use later.
```
    python ./lonestar_train.py
```

Classification Serrvice
===============
Provides an end-point that performs classifications via REST API calls.

**Start the service (development only):**
```
    python ./dicebox_service.py
```

**Production Deployment**

I've tested running dicebox with uwsgi, and proxied through nginx.  Nginx configurations can be found within ./nginx of this repository.
```
uwsgi --http-socket 127.0.0.1:5000 --manage-script-name --mount /=dicebox_service.py --plugin python,http --enable-threads --callable app —master
```


Dicebox Service API
===========

Default URL for API: `http(s)://{hostname}:5000/`


### Anonymous End-Points


* **Get Service API Version**

For verification of service API version.

```
    [GET] /api/version
```

Result:
`
{
    "version": "String"
}
`

* **Get Service Health**
 
For use in load balanced environments.

```
    [GET] /health/plain
```
Result:
`true` or `false` with a `201` status code.


### Authentication Required End-Points


**Request Header**

The below end-points require several headers to be present on the request.

```
    'Content-type': 'application/json',
    'API-ACCESS-KEY': 'String',
    'API-VERSION': 'String'
```

* API-ACCESS-KEY: 'A unique (secret) guid used for authorization'
* API-VERSION: 'Version of the API to use'

* **Classification**

Used to classify the image data.  Return the label index for the classification.


```
    [POST] /api/classify
```
Post Body: `{ "data": "Base64 encoded PNG image" }`

Result: `{ "classification": integer }`


Example
```
    {
        "classification": 7
    }

```
* **Get Categories**

 Used to turn classification results into human-readable labels.

```
    [GET] /api/categories
```
Result: A list of label to index mappings.

Example

```
    {
        "category_map": {
            "0": "1d4_1",
            "1": "1d4_2",
            "2": "1d4_3",
            "3": "1d4_4",
            "4": "1d6_1",
            "5": "1d6_2",
            "6": "1d6_3",
            "7": "1d6_4",
            "8": "1d6_5",
            "9": "1d6_6",
            "10": "unknown"
        }
    }
```



Sensory Service
===============
Provides an end-point that performs input data storage and retrieval via REST API calls.

**Start the service (development only):**
```
    python ./sensory_service.py
```

**Production Deployment**

I've tested running the sensory service with uwsgi, and proxied through nginx.  Nginx configurations can be found within ./nginx of this repository.
```
uwsgi --http-socket 127.0.0.1:5000 --manage-script-name --mount /=sensory_service.py --plugin python,http --enable-threads --callable app —master
```

* Stores data with classifications that are sent to it from the client/supervisored trainer.
* Provides data sets for the stand-alone trainer while building the weights.
    * For small batches of the data a single API call can be used.  
    * For large batches a batch order is created and the trainer polls the sensory service to get all the training data. (The sensory service pulls the data off a RabbitMQ queue with a matching batch order id.)


Sensory Service Batch Processor
===============================

A worker service that processes batch orders from a RabbitMQ task queue, and publishes back for a consumer.

**Start the service:**
```
    python ./sensory_service_batch_processor.py
```
The service reads data for the datasets off an AWS EFS which can be shared amoungst a large number of workers.


Client Consumption
==================
Sample client application.  Useful for supervised training.

[![Dicebox 60x50 Dataset Real-Time Image Classification Demo](http://img.youtube.com/vi/01MML66v4-U/0.jpg)](http://www.youtube.com/watch?v=01MML66v4-U)

```
    python ./legacy/dicebox_client.py
```

A simple test harness for running the datasets against the dicebox service.
```
    python ./dicebox_test_client.py
```


Mission Statement / Why
-----------------------
I set out on this adventure in the hope that one day I can play Dungeons and Dragons live online and have REAL dice involved.

There are lots of great programs with shared dice rollers in them. There's even VR, and augmented reality.  I know.


But, what I want is the real deal.  I want to be able grab my die, roll it, and have the experience shared easily.

Specifically, I want something:
* Real-time 
* Easy to use
* Able to use any camera and viewing angle available
* Usable by more than a single person
* Not require special/expensive setups
* Easy to connect to other applications, services, or devices
* Be beautiful (filled with as much love, art, and beauty that I can)
* Be magical (be of sufficiently advanced technology as to be indistinguishable from magic)
* Be itself a device/system that can stand alone with the above stated abilities


Dicebox has come through a number of iterations to get to where it is today.  I suspect it will probably have more, and may even evolve beyond anything I have yet to image. ;)


Data Sets
---------
[Download](https://s3-us-west-2.amazonaws.com/diceboximages/dist/dicebox_60x50.070817.tar.gz)
 | Dicebox Dataset 60x50 | approx 265k  gray scale png images of 1d4 and 1d6 dices.


### The creation the dataset
Using the below equipment and the supervised training program the images were generated over successive sessions.

#### Equipment

* [Logitech C930e USB Webcam](https://www.amazon.com/gp/product/B00CRJWW2G/ref=oh_aui_search_detailpage?ie=UTF8&psc=1)
* [Polaroid 8" Heavy Duty Mini Tripod](https://www.amazon.com/gp/product/B004OAFO0I/ref=oh_aui_search_detailpage?ie=UTF8&psc=1)
* [Rotating Display Turntable](https://www.amazon.com/gp/product/B0144DMXEO/ref=oh_aui_detailpage_o02_s00?ie=UTF8&psc=1)
* [DragonSteel Solid Metal Polyhedral 7 Die D&D Dice Set](https://www.amazon.com/gp/product/B01LW6QSFX/ref=oh_aui_detailpage_o01_s00?ie=UTF8&psc=1)


Weights
-------
[Download](https://s3-us-west-2.amazonaws.com/diceboxweights/weights.epoch_224.final.2017-07-12_16_26_10_253809.hdf5.tar.gz) | 
Dicebox weights trained on the above dataset.

To use the weights file, download and extract into the `./weights` directory.  By default the service will look for a weights file named `weights.best.hdf5`.  You'll want to rename/copy this file or update the relavent setting within the `dicebox.config` file.

**dicebox.config settings for the above sample weights file**
```
[DATASET]
categories = 11
image_width = 60
name = dicebox
image_height = 50
```
```
[LONESTAR]
neurons = 987
layers = 3
activation = elu
optimizer = adam
```

#### Equipment
Training was done with Tensorflow configured to use a GeForce 1080.


References
----------

[Matt Harvey](https://github.com/harvitronix) thank you, for without you dicebox would not be.  Much of the current implementation of dicebox comes from Matt's project below.  I originally forked Matt's work and used it until it outgrew what it was.

* [Blog Post](https://blog.coast.ai/lets-evolve-a-neural-network-with-a-genetic-algorithm-code-included-8809bece164) & [Code](https://github.com/harvitronix/neural-network-genetic-algorithm)

**Projects that I worked with heavily during prior implementations of dicebox**

* [Tensorflow & the 'slim' samples](https://github.com/tensorflow/tensorflow)
* [Tensorflow models](https://github.com/tensorflow/models)
* [EasyTensorflow](https://github.com/calvinschmdt/EasyTensorflow)

**Additional projects used here, or were reference material for dicebox**

* D20 Roll Fairness Evaluation | [Blog Post](http://www.markfickett.com/stuff/artPage.php?id=389) & [Code](https://github.com/markfickett/dicehistogram)
* Keras | [Site](https://keras.io/) & [Code](https://github.com/fchollet/keras)
* [JPG-and-PNG-to-MNIST](https://github.com/gskielian/JPG-PNG-to-MNIST-NN-Format)


Contributing
------------
1. Fork the repository on Github
2. Create a named feature branch (like `add_component_x`)
3. Write your change
4. Write tests for your change (if applicable)
5. Run the tests, ensuring they all pass
6. Submit a Pull Request using Github

License and Authors
-------------------
MIT License

Copyright (c) 2017-2020 Joshua C. Burt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
