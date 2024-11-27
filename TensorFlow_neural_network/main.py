import keras
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt


fashion_mnist = tf.keras.datasets.fashion_mnist

(train_images, train_labels), (test_images, test_labels) = fashion_mnist.load_data()

class_names = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
               'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']

train_images = train_images/255.0
test_images = test_images/255.0

model = keras.Sequential([
    keras.layers.Flatten(input_shape=(28, 28)), # Слой для того что бы расплющить данные на 28x28 pixel
    keras.layers.Dense(128, activation='relu'), # Слой где задается количество нейронов(128), relu(rectified linear unit) метод работы нейронов
    keras.layers.Dense(10, activation='softmax') # Слой последний(output) где количество нейронов 10, softmax метод камкует все данные в единую картину
])

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(train_images, train_labels, epochs=5)

