(function (doc, nav) {
    "use strict";

    var accessKeyGuid = '6e249b5f-b483-4e0d-b50b-81d95e3d9a59';
    var apiVersion = '0.2.2';
    var dicebox_service_url = 'http://localhost:5000';
    var sensory_service_url = 'http://localhost:5000';

    var video, width, height, context;
    var encoded_data;

    var classification;
    var results;

    var categories;
    var categoriesPanel;
    var categoriesString = '';

    var recordButton;
    var recordCategory;
    var flag_record = false;

    var statusString = '';
    var statusPanel;

    function get_record_flag() {
        return flag_record;
    }

    function set_record_flag(state) {
        flag_record = state;
        //console.log(flag_record);
    }

    function recordButtonClick() {
        set_record_flag(!get_record_flag());
    }

    function buildStatus() {
        statusString = '';
        statusString = statusString + 'capturing: ';
        statusString = statusString + flag_record;
        //console.log(statusString);
        return statusString;
    }

    function buildCategories() {
        var categoriesString = '<form>';
        for (var p in categories) {
            if (categories.hasOwnProperty(p)) {
                categoriesString += '<input type="radio" name="' + 'categoriesRadioBtn' + '" id="' + categories[p] + '">' + categories[p] + '<br>';
            }
        }
        categoriesString += '</form>';
        return categoriesString;
    }

    function updateStatus() {
        statusPanel.innerHTML = buildStatus();
    }

    function updateCategories() {
        categoriesPanel.innerHTML = buildCategories();
    }

    function initialize() {
        // The source video.
        video = doc.getElementById("video");
        width = video.width;
        height = video.height;

        // The target canvas.
        var canvas = doc.getElementById("canvas");
        context = canvas.getContext("2d");

        // results info panel
        results = doc.getElementById("results");

        statusPanel = doc.getElementById("statuspanel");

        categoriesPanel = doc.getElementById("categoriespanel");

        // set server categories
        init_server_categories();

        // build the initial status panel
        updateStatus();

        // Get the webcam's stream.
        nav.getUserMedia({video: true}, startStream, function () {});

        recordButton = doc.getElementById("recordButton");
        recordButton.addEventListener("click", function(){
            recordButtonClick();
            updateStatus();
        });
    }

    function startStream(stream) {
        video.src = URL.createObjectURL(stream);
        video.play();

        // Ready! Let's start drawing.
        requestAnimationFrame(draw);
    }

    function draw() {
        var frame = readFrame();

        if (frame) {
            // perform transform on input data
            // e.g. make gray scale
            makeGrayScale(frame.data)
            context.putImageData(frame, 0, 0);

            var dataURL = canvas.toDataURL();
            encoded_data = dataURL.replace(/^data:image\/png;base64\,/, "")
            //console.log(encoded_data);

            var json_packet={"data":encoded_data};
            var json_out = JSON.stringify(json_packet);
            //console.log(json_out);

            $.ajax({
                url: dicebox_service_url + '/api/classify',
                type: 'POST',
                headers:
                    {
                        'Content-type': 'application/json',
                        'API-ACCESS-KEY': accessKeyGuid,
                        'API-VERSION': apiVersion
                    },
                data: json_out,
                success: function(data) {
                    set_classification(categories[data.classification]);
                    results.innerHTML = 'classification: ' + get_classification();

                    if (get_record_flag() == true)
                    {
                        // we only care to captur training data when we don't match the expected outcome
                        if (get_training_category() != categories[data.classification]) {
                            sensory_store('dicebox', 100, 100, get_training_category(), encoded_data);
                        }
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    results.innerHTML = 'classification: ERROR ' + textStatus + ", " + errorThrown;

                    if (get_record_flag() == true)
                    {
                        sensory_store('dicebox', 100, 100, 'unclassified', encoded_data);
                    }
            }
            });

        }

        // Wait for the next frame.
        requestAnimationFrame(draw);
    }

    function sensory_store(name, width, height, category, encoced_data) {
        var json_packet={
            "name":name,
            "width": width,
            "height": height,
            "category": category,
            "data": encoded_data
        };
        var json_out = JSON.stringify(json_packet);
        $.ajax({
            url: sensory_service_url + '/api/sensory/store',
            type: 'POST',
            headers:
                {
                    'Content-type': 'application/json',
                    'API-ACCESS-KEY': accessKeyGuid,
                    'API-VERSION': apiVersion
                },
            data: json_out,
            success: function(data) {
                console.log('success!')
            }
        });
    }

    function readFrame() {
        try {
            var sourceX = width/2 - 50;
            var sourceY = height/2 - 50;

            //var sourceWidth = width;
            //var sourceHeight = height;
            var sourceWidth = 100;
            var sourceHeight = 100;

            var destWidth = 100;
            var destHeight = 100;
            //var destX = width / 2 - destWidth / 2;
            //var destY = height / 2 - destHeight / 2;
            var destX = 0;
            var destY = 0;
            context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, destX, destY, destWidth, destHeight);
            //context.drawImage(video, width/2 - 50, height/2 - 50, width/2 + 50, height/2 + 50, 0, 0, 100, 100);
        } catch (e) {
            // The video may not be ready, yet.
            return null;
        }
        return context.getImageData(0, 0, destWidth, destHeight);
    }

    function makeGrayScale(data) {
        var len = data.length;
        var luma;

        for (var i = 0; i < len; i += 4) {
            luma = data[i] * 0.2126 + data[i+1] * 0.7152 + data[i+2] * 0.0722;
            data[i] = data[i+1] = data[i+2] = luma;
        }
    }

    function init_server_categories() {
        $.ajax({
            url: dicebox_service_url + '/api/categories',
            type: 'GET',
            headers:
                {
                    'Content-type': 'application/json',
                    'API-ACCESS-KEY': accessKeyGuid,
                    'API-VERSION': apiVersion
                },
            success: function(data) {
                set_categories(data.category_map);
                updateCategories();
            }
        });

    }

    function set_categories(category_map) {
        categories = category_map;
    }

    function get_training_category() {
        var trainingCategoryForm = doc.forms[0];
        var selectedCategory = '';
        var i;
        for (i = 0; i < trainingCategoryForm.length; i++) {
            //console.log('josh');
            if (trainingCategoryForm[i].checked) {
                //selectedCategory = trainingCategoryForm[i].value;
                selectedCategory = trainingCategoryForm[i].id;
            }
        }
        //console.log(selectedCategory);
        return selectedCategory;
    }

    function get_classification() {
        return classification;
    }

    function set_classification(returned_classification) {
        classification = returned_classification;
    }

    addEventListener("DOMContentLoaded", initialize);
})(document, navigator);
