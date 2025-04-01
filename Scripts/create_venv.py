import os
import subprocess

def main():
    if os.path.exists("venv"):
        print("Виртуальное окружение уже существует.")
        return

    print("Создаём виртуальное окружение...")
    subprocess.run(["python3", "-m", "venv", "venv"])

    activate_script = "venv/Scripts/activate" if os.name == "nt" else "source venv/bin/activate"
    print("Активируем виртуальное окружение...")
    subprocess.run(activate_script, shell=True, executable="/bin/bash")

    if os.path.exists("requirements.txt"):
        print("Устанавливаем зависимости из requirements.txt...")
        subprocess.run(["pip", "install", "-r", "requirements.txt"])
    else:
        print("Файл requirements.txt не найден. Установите зависимости вручную.")

if __name__ == "__main__":
    main()

# Запуск: python create_venv.py
