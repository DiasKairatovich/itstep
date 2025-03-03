class Pizza:
    def __init__(self, name, dough, sauce, species, price):
        self.name = name
        self.dough = dough
        self.sauce = sauce
        self.species = species
        self.price = price

    def prepare(self):
        print(f"\nГотовим {self.name}: замешиваем тесто ({self.dough}), добавляем соус ({self.sauce}), добавляем начинку ({self.species})")
        print(f"Выпекаем {self.name}...")
        print(f"Режем {self.name}...")
        print(f"Упаковываем {self.name}...")

########################################################################################################################

class Order:
    def __init__(self):
        self.pizzas = []

    def add_pizza(self, pizza):
        if len(self.pizzas) < 4:
            self.pizzas.append(pizza)
            print(f"{pizza.name} добавлена в заказ.")
        else:
            print("Нельзя заказать больше 4 пицц!")

    def total_price(self):
        total = 0
        for pizza in self.pizzas:
            total += pizza.price
        return total

    def process_order(self):
        print("\nНачинаем приготовление заказа...")
        for pizza in self.pizzas:
            pizza.prepare()
        print("\nЗаказ готов!")

########################################################################################################################

class Terminal:
    def __init__(self):
        self.menu = [
            Pizza("Пепперони", "тонкое тесто", "томатный соус", "пепперони, моцарелла", 700),
            Pizza("Барбекю", "толстое тесто", "барбекю соус", "курица, бекон, лук, моцарелла", 800),
            Pizza("Дары Моря", "тонкое тесто", "белый соус", "креветки, кальмары, мидии, моцарелла", 900)
        ]

    def display_menu(self):
        print("Меню:")
        for i, pizza in enumerate(self.menu, 1):
            print(f"{i}. {pizza.name} - {pizza.price} тенге")

    def take_order(self):
        order = Order()
        while True:
            self.display_menu()
            choice = input("\nВведите номер пиццы для заказа (или '0' для завершения): ")

            if choice == '0':
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(self.menu):
                order.add_pizza(self.menu[int(choice) - 1])
            else:
                print("Неверный ввод. Попробуйте снова.")

        total = order.total_price()
        print(f"\nИтого к оплате: {total} тенге")


        confirm = input("Подтвердить заказ? (да/нет): ").strip().lower()
        if confirm == 'да':
            print("Оплата принята. Заказ обрабатывается...")
            order.process_order()
        else:
            print("Заказ отменен.")



if __name__ == "__main__":
    terminal = Terminal()
    terminal.take_order()
    input("\nНажмите Enter для выхода...")
