# 6. Итераторы и генераторы: Реализуйте генератор, который бесконечно
# выдает случайные пароли длиной 8 символов.
# import random
# def pass_gen():
#     alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
#     while True:
#         password = ''
#         for i in range(8):
#             password += random.choice(alphabet)
#         yield password
# for password in pass_gen():
#     print(password)
#-----------------------------------------------------------------------------------------------------------------------
# 7. Работа с датами: Напишите программу, которая определяет, сколько
# дней осталось до ближайшего дня рождения пользователя, учитывая
# текущую дату.
# import datetime
# today = datetime.date.today()
# def days_until_birthday(birthday):
#     birthday = datetime.datetime.strptime(birthday, "%d.%m.%Y").date()
#     delta = birthday.replace(year=today.year) - today
#     if delta.days < 0:
#         delta = birthday.replace(year=today.year + 1) - today
#     return delta.days
#
# birthday = input("День рождения (дд.мм.гг): ")
# calc = days_until_birthday(birthday)
# print(f"Оталось до ближайшего дня рождения: {calc} дней")

#-----------------------------------------------------------------------------------------------------------------------
# 8. Обработка исключений: Напишите программу, которая запрашивает
# у пользователя число и делит 100 на это число. Обработайте
# возможные исключения (ZeroDivisionError, ValueError).
# def calc():
#     try:
#         num = int(input(f"Введите ваше число: "))
#         res = int(100/num)
#         print(res)
#     except ZeroDivisionError as zero_error:
#         print(f"Zero number error: {zero_error}")
#     except ValueError as value_error:
#         print(f"Variable type error:{value_error}")
#     except Exception as error:
#         print(f"Any other error: {error}")
#
# calc()

#-----------------------------------------------------------------------------------------------------------------------
# 9. ООП: Реализуйте класс BankAccount с методами deposit() и withdraw(),
# которые изменяют баланс. Добавьте проверку, чтобы нельзя было
# снять больше, чем есть на счете.
# class BankAccount:
#     def __init__(self, balance: int):
#         self.balance = balance
#
#     def deposit(self, amount):
#         if amount < 0:
#             print("Нельзя добавить отрецатильное число на депозит")
#         else:
#             self.balance += amount
#             print(self.balance)
#
#     def withdraw(self, amount):
#         if self.balance > amount:
#             self.balance -= amount
#             print(self.balance)
#         elif self.balance == amount:
#             print("Нельзя оставить депозит пустым!")
#         else:
#             print("Сумма снятия превышает суммы на балансе !")
#
# user = BankAccount(1000)
# # user.deposit(100)
# user.withdraw(150)

#-----------------------------------------------------------------------------------------------------------------------
# 10.Многозадачность: Напишите программу, которая создает три потока.
# Первый поток записывает числа от 1 до 10 в файл, второй поток
# считывает их, третий — выводит сумму этих чисел.

import threading

filename = "test.txt"

# Функция первого потока
def write_numbers():
    with open(filename, "w") as file:
        for i in range(10):
            file.write(str(i+1) + " ")
            print(f"Записано число: {i+1}")
    print(f"Числа записаны в файл {filename}")

# Функция второго потока
def read_numbers():
    with open(filename, "r") as file:
        numbers = []
        for num in file.read().split():
            numbers.append(int(num))
    print(f"Числа считаны с файла {filename}:", numbers)
    return numbers

# Функция третьего потока
def calculate_sum():
    with open(filename, "r") as file:
        numbers = []
        for num in file.read().split():
            numbers.append(int(num))
    print("Сумма чисел:", sum(numbers))


#Запуск каждого потока поэтапно
thread1 = threading.Thread(target=write_numbers)
thread1.start()
thread1.join()

thread2 = threading.Thread(target=read_numbers)
thread2.start()
thread2.join()

thread3 = threading.Thread(target=calculate_sum)
thread3.start()
thread3.join()

