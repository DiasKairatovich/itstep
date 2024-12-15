from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "1b77c234efc86907a3edbbf86ba8492f7e4e98548f293cb97ac55fd42444a657"

# Initialize database
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        payment_status INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            option_1 TEXT NOT NULL,
            option_2 TEXT NOT NULL,
            option_3 TEXT NOT NULL,
            option_4 TEXT NOT NULL
        )
        """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        answers TEXT NOT NULL,
        test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)


    conn.commit()
    conn.close()

init_db()

# Helper functions
def add_user(name, email):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
    user_id = cursor.lastrowid  # Получаем ID нового пользователя
    conn.commit()
    conn.close()
    return user_id  # Возвращаем ID

def save_result(user_id, answers):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO results (user_id, answers) VALUES (?, ?)", (user_id, answers))
    conn.commit()
    conn.close()

def update_payment_status(user_id, status=1):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET payment_status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()

# Routes
@app.route("/")
def index():
    # Если нет user_id в сессии, перенаправляем на страницу регистрации/входа
    if "user_id" not in session:
        return redirect(url_for("register"))  # Если пользователь уже зарегистрирован, сразу перенаправляем на тест
    return render_template("index.html")  # Перенаправляем на тест, если пользователь уже зарегистрирован

@app.route("/register", methods=["GET", "POST"])
def register():
    # Если user_id уже есть в сессии, очищаем сессию для принудительной авторизации
    session.pop("user_id", None)

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        # Проверяем, существует ли пользователь с таким email
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            # Если пользователь найден в базе, сохраняем его id в сессии
            session["user_id"] = user[0]
            return redirect(url_for("test"))  # Перенаправляем на страницу теста
        else:
            # Если пользователь не найден, регистрируем нового
            user_id = add_user(name, email)
            session["user_id"] = user_id  # Сохраняем id нового пользователя в сессии
            return redirect(url_for("test"))
    return render_template("register.html") # Показываем страницу регистрации/входа


@app.route("/test", methods=["GET", "POST"])
def test():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT payment_status FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return "Ошибка: Пользователь не найден!", 404

    payment_status = result[0]
    if payment_status == 0:
        return redirect(url_for("payment"))

    if request.method == "POST":
        answers = request.form["q1"]
        save_result(user_id, answers)
        return redirect(url_for("result"))

    return render_template("test.html")

@app.route("/payment")
def payment():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))
    update_payment_status(user_id)
    return redirect(url_for("test"))

@app.route("/result")
def result():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))

    # Подключаемся к базе данных
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Получаем ответы пользователя
    cursor.execute("SELECT answers, test_date FROM results WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return "Результаты теста не найдены!"  # Если нет результатов

    user_answers, test_date = result

    # Пример правильных ответов (можно хранить их в базе или в отдельном файле)
    correct_answers = {
        "q1": "A",  # Вопрос 1: ответ "A"
        "q2": "C",  # Вопрос 2: ответ "C"
        "q3": "B",  # Вопрос 3: ответ "B"
    }

    # Разбираем ответы пользователя (если это строка формата JSON)
    import json
    try:
        user_answers = json.loads(user_answers)  # Например: {"q1": "A", "q2": "B", "q3": "B"}
    except json.JSONDecodeError:
        return "Ошибка в формате сохранённых ответов!"

    # Сравниваем ответы и подсчитываем баллы
    score = 0
    total_questions = len(correct_answers)
    for question, correct_answer in correct_answers.items():
        if user_answers.get(question) == correct_answer:
            score += 1

    # Передаем данные в шаблон
    return render_template(
        "result.html",
        score=score,
        total_questions=total_questions,
        test_date=test_date,
        correct_answers=correct_answers,
        user_answers=user_answers
    )

if __name__ == "__main__":
    app.run(debug=True)


