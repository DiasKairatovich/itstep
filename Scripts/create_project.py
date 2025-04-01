import os
import sys
import subprocess

def run_command(command, shell=False):
    """Запускает команду в терминале."""
    result = subprocess.run(command, shell=shell, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Ошибка: {result.stderr}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Ошибка: укажите имя проекта!")
        print("Использование: python create_project.py project_name")
        sys.exit(1)

    project_name = sys.argv[1]

    # Создаём виртуальное окружение
    print("Создаём виртуальное окружение...")
    run_command(["python3", "-m", "venv", "venv"])

    # Активируем виртуальное окружение
    activate_script = "venv/Scripts/activate" if os.name == "nt" else "source venv/bin/activate"
    print("Активируем виртуальное окружение...")
    run_command(activate_script, shell=True)

    # Устанавливаем Django
    print("Устанавливаем Django...")
    run_command(["pip", "install", "--upgrade", "pip"])
    run_command(["pip", "install", "django"])

    # Создаём Django-проект
    print(f"Создаём Django-проект: {project_name}...")
    run_command(["django-admin", "startproject", project_name, "."])

    # Создаём приложение (например, core)
    print("Создаём приложение core...")
    run_command(["python", "manage.py", "startapp", "core"])

    # Замораживаем зависимости
    print("Сохраняем зависимости в requirements.txt...")
    run_command(["pip", "freeze"], shell=True)
    with open("requirements.txt", "w") as f:
        f.write(subprocess.run(["pip", "freeze"], capture_output=True, text=True).stdout)

    print(f"Проект {project_name} создан и настроен!")

if __name__ == "__main__":
    main()

# Запуск: python create_project.py project_name
