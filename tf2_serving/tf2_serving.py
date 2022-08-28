# Copyright 2019 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Generated by nuclio.export.NuclioExporter

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

import json
import numpy as np
import requests
from tensorflow import keras
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.preprocessing.image import load_img
from os import environ, path
from PIL import Image
from io import BytesIO
from urllib.request import urlopen
import mlrun


class TFModel(mlrun.runtimes.MLModelServer):
    def __init__(self, name: str, model_dir: str):
        super().__init__(name, model_dir)

        self.IMAGE_WIDTH = int(environ.get("IMAGE_WIDTH", "128"))
        self.IMAGE_HEIGHT = int(environ.get("IMAGE_HEIGHT", "128"))

        try:
            with open(environ["classes_map"], "r") as f:
                self.classes = json.load(f)
        except:
            self.classes = None

    def load(self):
        model_file, extra_data = self.get_model(".h5")
        self.model = load_model(model_file)

    def preprocess(self, body):
        try:
            output = {"instances": []}
            instances = body.get("instances", [])
            for byte_image in instances:
                img = Image.open(byte_image)
                img = img.resize((self.IMAGE_WIDTH, self.IMAGE_HEIGHT))

                x = image.img_to_array(img)
                x = np.expand_dims(x, axis=0)
                output["instances"].append(x)

            output["instances"] = [np.vstack(output["instances"])]
            return output
        except:
            raise Exception(f"received: {body}")

    def predict(self, data):
        images = data.get("instances", [])

        predicted_probability = self.model.predict(images)

        return predicted_probability

    def postprocess(self, predicted_probability):
        if self.classes:
            predicted_classes = np.around(predicted_probability, 1).tolist()[0]
            predicted_probabilities = predicted_probability.tolist()[0]
            return {
                "prediction": [
                    self.classes[str(int(cls))] for cls in predicted_classes
                ],
                f'{self.classes["1"]}-probability': predicted_probabilities,
            }
        else:
            return predicted_probability.tolist()[0]
