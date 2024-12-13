import matplotlib.pyplot as plt
import re
import shutil
import string

import tensorflow as tf
import os
# Suppress oneDNN and GPU detection
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
# Reduce TensorFlow log verbosity
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from tensorflow.keras import layers
from tensorflow.keras import losses

dataset = tf.keras.utils.get_file("aclImdb_v1", "/home/dias/PycharmProjects/study/TensorFlow_NN/aclImdb_v1", untar=True, cache_dir='.', cache_subdir='')

dataset_dir = os.path.join(os.path.dirname(dataset), 'aclImdb_v1/aclImdb')
# print(os.listdir(dataset_dir))

train_dir = os.path.join(dataset_dir, 'train')
# print(os.listdir(train_dir))

# sample_file = os.path.join(train_dir, 'pos/1181_9.txt')
# with open(sample_file) as f:
#   print(f.read())

# remove_dir = os.path.join(train_dir, 'unsup')
# shutil.rmtree(remove_dir)

batch_size = 32
seed = 42
raw_train_ds = tf.keras.utils.text_dataset_from_directory(
    'aclImdb_v1/aclImdb/train',
    batch_size=batch_size,
    validation_split=0.2,
    subset='training',
    seed=seed)
raw_val_ds = tf.keras.utils.text_dataset_from_directory(
    'aclImdb_v1/aclImdb/train',
    batch_size=batch_size,
    validation_split=0.2,
    subset='validation',
    seed=seed)
raw_test_ds = tf.keras.utils.text_dataset_from_directory(
    'aclImdb_v1/aclImdb/test',
    batch_size=batch_size)


def custom_standardization(input_data): # тут удаляем лишние знаки для обрабтки текста корректно
  lowercase = tf.strings.lower(input_data)
  stripped_html = tf.strings.regex_replace(lowercase, '<br />', ' ')
  return tf.strings.regex_replace(stripped_html,
                                  '[%s]' % re.escape(string.punctuation),
                                  '')


max_features = 10000
sequence_length = 250

vectorize_layer = layers.TextVectorization( # тут задаются индексы каждому найденному слову
    standardize=custom_standardization,
    max_tokens=max_features,
    output_mode='int',
    output_sequence_length=sequence_length)

train_text = raw_train_ds.map(lambda x, y: x) # тренируем нашу модель
vectorize_layer.adapt(train_text)

def vectorize_text(text, label): # функцию, чтобы увидеть результат использования этого слоя
  text = tf.expand_dims(text, -1)
  return vectorize_layer(text), label


text_batch, label_batch = next(iter(raw_train_ds))
first_review, first_label = text_batch[0], label_batch[0]
# print("Review", first_review)
# print("Label", raw_train_ds.class_names[first_label])
# print("Vectorized review", vectorize_text(first_review, first_label))

### тут мы можем проверить что 1287 означает такое то слово !!!
# print("1287 ---> ",vectorize_layer.get_vocabulary()[1287])


train_ds = raw_train_ds.map(vectorize_text)
val_ds = raw_val_ds.map(vectorize_text)
test_ds = raw_test_ds.map(vectorize_text)



### .cache() сохраняет данные в памяти после их загрузки с диска. Это гарантирует, что набор данных не станет узким местом при обучении вашей модели.
### .prefetch() перекрывает предварительную обработку данных и выполнение модели во время обучения.
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)
test_ds = test_ds.cache().prefetch(buffer_size=AUTOTUNE)

####################################################################################################################################
# Создание модели
'''
Первый слой — это слой Embedding . Этот слой принимает обзоры в целочисленном кодировании и ищет вектор встраивания для 
каждого индекса слова. Эти векторы изучаются по мере обучения модели. Векторы добавляют измерение к выходному массиву. 
Результирующие размеры: (batch, sequence, embedding) . Чтобы узнать больше о встраиваниях, см. руководство по встраиванию слов .

Затем слой GlobalAveragePooling1D возвращает выходной вектор фиксированной длины для каждого примера путем усреднения по 
измерению последовательности. Это позволяет модели обрабатывать ввод переменной длины самым простым способом.

Этот выходной вектор фиксированной длины передается через полносвязный ( Dense ) слой с 16 скрытыми единицами.

Последний слой плотно связан с одним выходным узлом.
'''
embedding_dim = 16
model = tf.keras.Sequential([
  layers.Embedding(max_features + 1, embedding_dim),
  layers.Dropout(0.2),
  layers.GlobalAveragePooling1D(),
  layers.Dropout(0.2),
  layers.Dense(1)])
model.summary()
####################################################################################################################################


model.compile(loss=losses.BinaryCrossentropy(from_logits=True), optimizer='adam', metrics=tf.metrics.BinaryAccuracy(threshold=0.0))

# Обучите модель
epochs = 10
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=epochs)


# Оценить модель
loss, accuracy = model.evaluate(test_ds)
print("Loss: ", loss)
print("Accuracy: ", accuracy)
