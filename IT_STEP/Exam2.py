# import random
#
# def game():
#     print("Добро пожаловать в игру 'Камень, ножницы, бумага'")
#
#     choices = ["Камень", "Ножницы", "Бумага"]
#
#     while True:
#         print("Вам на выбор даются три варианта: Камень, Ножницы, Бумага")
#         comp_choice = random.choice(choices)
#         your_choice = input("Введите ваш выбор: ").capitalize()
#
#         if your_choice not in choices:
#             print("Ошибка ввода! Попробуйте снова.")
#             continue
#
#         print(f"Компьютер выбрал: {comp_choice}")
#
#         if comp_choice == your_choice:
#             print("Ничья")
#         elif comp_choice == "Камень" and your_choice == "Ножницы":
#             print("Выйграл компьютер")
#         elif comp_choice == "Ножницы" and your_choice == "Камень":
#             print("Вы выйграли")
#
#         elif comp_choice == "Бумага" and your_choice == "Камень":
#             print("Выйграл компьютер")
#         elif comp_choice == "Камень" and your_choice == "Бумага":
#             print("Вы выйграли")
#
#         elif comp_choice == "Ножницы" and your_choice == "Бумага":
#             print("Выйграл компьютер")
#         elif comp_choice == "Бумага" and your_choice == "Ножницы":
#             print("Вы выйграли")
#
#
#         play_again = input("Хотите сыграть ещё раз? (да/нет): ").strip().lower()
#         if play_again != "да":
#             print("Спасибо за игру!")
#             break
#
# game()

########################################################################################################################

# import random
#
# def game2():
#     print("Добро пожаловать в игру 'Угадай число'")
#     print("Компьютер выбрал число от 1 до 100. Попробуйте его угадать.")
#
#     comp_number = random.randint(1, 100)
#     attempts = 0
#
#     while True:
#         try:
#             your_number = int(input("Введите ваш выбор: "))
#             attempts += 1
#
#             if your_number < comp_number:
#                 print("Загаданное число больше!")
#             elif your_number > comp_number:
#                 print("Загаданное число меньше!")
#             else:
#                 print(f"Поздравляю! Вы угадали число {comp_number} за {attempts} попыток.")
#                 break
#         except ValueError:
#             print("Ошибка ввода! Попробуйте снова.")
#
# game2()

########################################################################################################################

import random

def game3():
    print("Добро пожаловать в игру 'Виселица'")
    print("Компьютер загадал слово, попробуйте его угадать.")
    print("---"*20)
    words = ["apple", "mango", "banana", "kiwi", "orange", "strawberry", "grapefruit"]
    comp_word = random.choice(words).lower()
    attempts = 7
    buffer = set()

    guessed = ["_"] * len(comp_word) #блюрит все слово целиком


    while attempts > 0 and "_" in guessed:
        print("Слово:", " ".join(guessed))
        print(f"Количество попыток: {attempts}")
        print(f"Использованные буквы: {', '.join(buffer) if buffer else 'Нет'}")
        your_guess = input(f"Введите букву: ").lower()

        #проверка на корректность ввода данных
        if len(your_guess) != 1:
            print("Введите только одну букву!")
        if your_guess in buffer:
            print("Вы уже называли данную букву")
            continue

        buffer.add(your_guess)

        #проверка на наличие буквы
        if your_guess in comp_word:
            print("Буква найдена в загаданном слове")
            for i, letter in enumerate(comp_word):
                if letter == your_guess:
                    guessed[i] = your_guess
        else:
            print("К сожалению такой буквы нет")
            attempts -= 1

    #Проверка остатка неразгаданных слов
    if "_" not in guessed:
        print(f"Поздравляем! Вы угадали слово: {comp_word}!")
    else:
        print(f"Вы проиграли! Загаданное слово было: {comp_word}")

game3()
