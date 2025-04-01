import os
import subprocess
import sys


def main():
    if not os.path.exists("venv"):
        print("Ошибка: Виртуальное окружение не найдено! Сначала запустите create_project.py")
        sys.exit(1)

    # Определяем команду для активации
    activate_script = "venv/Scripts/activate" if os.name == "nt" else "source venv/bin/activate"

    print("Активируем виртуальное окружение...")
    subprocess.run(activate_script, shell=True, executable="/bin/bash")

    print("Запускаем сервер Django...")
    subprocess.run(["python", "manage.py", "runserver"])


if __name__ == "__main__":
    main()

# Запуск: python run_project.py
