class Employee:
    employee_count = 0
    def __init__(self, name, position, salary):
        self.name = name
        self.position = position
        self.salary = salary
        Employee.employee_count += 1

    def give_raise(self, amount):
        self.salary += amount

    def total_employees(self):
        print(f"Total employees: {Employee.employee_count}")

    def __str__(self):
        return f"Employee: {self.name}, Position: {self.position}, Salary: {self.salary}"



class Manager(Employee):
    def __init__(self, name, salary):
        super().__init__(name, "Manager", salary)

    def work(self):
        print(f"Employee {self.name} manage with team and rule them")

class Developer(Employee):
    def __init__(self, name, salary):
        super().__init__(name, "Developer", salary)
    def work(self):
        print(f"Employee {self.name} works with developing code")


class Intern(Employee):
    def __init__(self, name, salary=0):
        super().__init__(name, "Intern", salary)
    def work(self):
        print(f"Intern {self.name} helps others and gain experience")

########################################################################################################################
manager = Manager("Алиса", 200000)
developer = Developer("Боб", 150000)
intern = Intern("Чарли")



print(manager)  # Сотрудник: Алиса, Должность: Manager, Зарплата: 200000 тенге
manager.work()  # Алиса управляет командой
print("-"*50)
print(developer)  # Сотрудник: Боб, Должность: Developer, Зарплата: 150000 тенге
developer.work()  # Боб пишет код
print("-"*50)
print(intern)  # Сотрудник: Чарли, Должность: Intern, Зарплата: 0 тенге
intern.work()  # Чарли проходит стажировку