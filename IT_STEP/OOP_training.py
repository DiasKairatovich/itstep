class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price


class Basket:
    def __init__(self):
        self.products = []

    def add_product(self, product):
        if len(self.products) < 5:
            self.products.append(product)
            print(f"Added product {product.name} with price {product.price}")
        else:
            print(f"No more than 5 products in basket")

    def total_price(self):
        total = 0
        for product in self.products:
            total += product.price
        return total

    def print_check(self):
        print("\nYour check:")
        for product in self.products:
            print(f"Product: {product.name}, Price: {product.price}")


class Terminal:
    def __init__(self):
        self.products = [
            Product("Stuff1", 1200),
            Product("Stuff2", 800),
            Product("Stuff3", 700),
            Product("Stuff4", 650),
            Product("Stuff5", 1150),
            Product("Stuff6", 450),
            Product("Stuff7", 570),
            Product("Stuff8", 840),
            Product("Stuff9", 345),
            Product("Stuff10", 980),
        ]

    def display_menu(self):
        print("Products to choose:")
        for i in range(len(self.products)):
            print(f"{i + 1}. {self.products[i].name} - {self.products[i].price}")

    def take_order(self):
        basket = Basket()
        while True:
            self.display_menu()
            choice = input(f"Choose products you need (from 1 to 10, or 0 to exit): ")

            if choice == "0":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(self.products):
                basket.add_product(self.products[int(choice) - 1])
            else:
                print("Incorrect input type")

        basket.print_check()
        total_price = basket.total_price()
        print(f"Total check price: {total_price}")


if __name__ == "__main__":
    terminal = Terminal()
    terminal.take_order()
