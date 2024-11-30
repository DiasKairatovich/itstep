import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import schedule
import time
from datetime import datetime

# Конфигурация почты
SMTP_SERVER = "smtp.gmail.com"  # Например, Gmail SMTP-сервер
SMTP_PORT = 587
EMAIL_ADDRESS = "diasshaymerdenov@gmail.com"  # Ваш email
EMAIL_PASSWORD = "gfou zurx dzwl bgso"  # Пароль приложения (App Password)

# Получатель письма
RECIPIENT = "shaymerdenov.dias@bk.ru"


# Функция для отправки письма с PDF
def send_email():
    try:
        # Настройка письма
        print("Отправка письма...")
        subject = "Отчет за месяц" # Заголовок письма
        body = "Добрый день! Пожалуйста, найдите во вложении отчет за месяц." # Подзаголовок

        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = RECIPIENT
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Присоединяем PDF
        filename = r"Resume.pdf"  # Укажите путь к вашему PDF
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}",
        )
        msg.attach(part)

        # Отправка письма
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT, msg.as_string())

        print("Письмо успешно отправлено!")

    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")


# Функция для проверки конкретной даты
def schedule_monthly_email():
    today = datetime.now()
    if today.day == 30:  # Если сегодня 30-е число месяца
        send_email()

# Планировщик
schedule.every().day.at("16:38").do(schedule_monthly_email)  # Проверяем каждый день в 16:38(тест)

print("Скрипт запущен. Ожидание отправки...")
while True:
    schedule.run_pending()
    time.sleep(1)
