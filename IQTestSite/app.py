from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import json

app = Flask(__name__)
app.secret_key = "1d6d9de2355aad9dae7d543a563153fd2f1c082c6bf788f159f07bd653e21965"

# Инициализация базы данных
DATABASE = "database.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Create the `users` table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL
        )
        """)
        # Create the `questions` table
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
        # Create the `results` table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            answers TEXT NOT NULL,
            test_date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        # Insert initial questions into the `questions` table
        questions = [
            (1, "In which year was St. Petersburg founded?", "A", "A: 1703", "B: 1800", "C: 1604", "D: 1750"),
            (2, "What is the capital of France?", "C", "A: Lyon", "B: Marseille", "C: Paris", "D: Nice"),
            (3, "Who wrote 'War and Peace'?", "D", "A: Gogol", "B: Chekhov", "C: Pushkin", "D: Tolstoy"),
            (4, "How many planets are there in the Solar System?", "B", "A: 7", "B: 8", "C: 9", "D: 10"),
            (5, "What is the capital of Australia?", "D", "A: Sydney", "B: Melbourne", "C: Brisbane", "D: Canberra"),
        ]
        # Insert questions if the table is empty
        cursor.execute("SELECT COUNT(*) FROM questions")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
               INSERT INTO questions (id, question_text, correct_answer, option_1, option_2, option_3, option_4)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               """, questions)
        conn.commit()

# Главная страница
@app.route("/")
def index():
    return render_template("index.html")

# Регистрация пользователя
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
            conn.commit()
            session["user_id"] = cursor.lastrowid
        return redirect(url_for("test"))
    return render_template("register.html")

# Страница с тестом
@app.route("/test")
def test():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, question_text, correct_answer, option_1, option_2, option_3, option_4 FROM questions")
        rows = cursor.fetchall()

    questions = [
        {
            "id": row[0],
            "question_text": row[1],
            "correct_answer": row[2],
            "options": [row[3], row[4], row[5], row[6]]
        } for row in rows
    ]

    return render_template("test.html", questions=questions)

# Обработка результатов теста
@app.route("/submit", methods=["POST"])
def submit():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))

    answers = {key: value for key, value in request.form.items()}
    test_date = request.form.get("test_date")

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO results (user_id, answers, test_date) VALUES (?, ?, ?)",
            (user_id, json.dumps(answers), test_date)
        )
        conn.commit()

    return redirect(url_for("result"))

# Страница с результатами
@app.route("/result")
def result():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT answers, test_date FROM results WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            return "Результаты теста не найдены!"

        user_answers, test_date = result
        cursor.execute("SELECT id, question_text, correct_answer FROM questions")
        questions = cursor.fetchall()

    question_data = {str(row[0]): {"text": row[1], "correct": row[2]} for row in questions}

    try:
        user_answers = json.loads(user_answers)
    except json.JSONDecodeError:
        return "Ошибка в формате сохранённых ответов!"

    score = 0
    total_questions = len(question_data)
    for question_id, data in question_data.items():
        if user_answers.get(question_id) == data["correct"]:
            score += 1

    return render_template(
        "result.html",
        score=score,
        total_questions=total_questions,
        test_date=test_date,
        correct_answers=question_data,
        user_answers=user_answers
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)


