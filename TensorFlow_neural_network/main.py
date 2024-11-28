import keras
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

fashion_mnist = tf.keras.datasets.fashion_mnist

(train_images, train_labels), (test_images, test_labels) = fashion_mnist.load_data()

class_names = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat', 'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']

train_images = train_images/255.0 # обучающии набор данных
test_images = test_images/255.0 # тестовый набор данных

model = keras.Sequential([
    # преобразует(переформатирует) формат изображений из двумерного массива (28 на 28 пикселей) в одномерный массив (28 * 28 = 784 пикселей)
    keras.layers.Flatten(input_shape=(28, 28)),

    # Полносвязный слой где задается количество нейронов(128), relu(rectified linear unit) метод работы нейронов
    keras.layers.Dense(128, activation='relu'),

    # Полносвязный слой последний(output) где количество нейронов(unit) 10, softmax метод камкует все данные в единую картину
    keras.layers.Dense(10, activation='softmax')
])

# Прежде чем модель будет готова к обучению, ей нужно еще несколько настроек.
model.compile(
    # Оптимизатор — именно так модель обновляется на основе данных, которые она видит, и ее функции потерь.
    optimizer='adam',

    # Функция потерь — измеряет, насколько точна модель во время обучения. Вы хотите минимизировать эту функцию, чтобы "направить" модель в правильном направлении.
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),

    # Метрики — используются для мониторинга этапов обучения и тестирования. В следующем примере используется точность , доля правильно классифицированных изображений.
    metrics=['accuracy']
)

# Начало обучения
model.fit(train_images, train_labels, epochs=10)

# Оценка точности
test_loss, test_acc = model.evaluate(test_images,  test_labels, verbose=2)
print('\nTest accuracy:', test_acc)
