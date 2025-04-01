import os
import subprocess

def main():
    if not os.path.exists("venv"):
        print("Ошибка: Виртуальное окружение не найдено!")
        return

    print("Сохраняем зависимости в requirements.txt...")
    with open("requirements.txt", "w") as f:
        f.write(subprocess.run(["pip", "freeze"], capture_output=True, text=True).stdout)

    print("✅ Файл requirements.txt обновлён!")

if __name__ == "__main__":
    main()

# Запуск: python freeze_requirements.py
