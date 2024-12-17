from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database initialization
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            answers TEXT NOT NULL,  -- Stores user answers as JSON
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

init_db()

questions = [
        {"id": 1, "question": "What is 2 + 2?", "options": ["3", "4", "5"], "answer": "4"},
        {"id": 2, "question": "What is the capital of France?", "options": ["Berlin", "London", "Paris"], "answer": "Paris"},
        {"id": 3, "question": "What is the square root of 9?", "options": ["2", "3", "4"], "answer": "3"},
    ]

# Forms
class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = generate_password_hash(form.password.data)
        try:
            with sqlite3.connect("database.db") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
                conn.commit()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                flash("Login successful!", "success")
                return redirect(url_for("test"))
            else:
                flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)

def save_result(user_id, answers):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # Convert answers dictionary to JSON
    answers_json = json.dumps(answers)
    cursor.execute("INSERT INTO results (user_id, answers) VALUES (?, ?)", (user_id, answers_json))
    conn.commit()
    conn.close()

@app.route("/test", methods=["GET", "POST"])
def test():
    user_id = session.get("user_id")
    if 'user_id' not in session:
        flash("Please log in to take the test.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect user answers
        answers = {}
        for question in questions:
            q_id = str(question["id"])
            answers[q_id] = request.form.get(q_id)

        # Save answers in the database
        save_result(user_id, answers)
        return redirect(url_for("result"))

    return render_template("test.html", questions=questions)

@app.route("/result")
def result():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))

    # Connect to the database
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Retrieve user answers
    cursor.execute("SELECT answers, test_date FROM results WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return "Test results not found!"

    answers_json, test_date = result
    user_answers = json.loads(answers_json)

    # Score calculation
    score = sum(1 for question in questions if user_answers.get(str(question["id"])) == question["answer"])
    total_questions = len(questions)

    return render_template(
        "result.html",
        score=score,
        total_questions=total_questions,
        test_date=test_date,
        questions=questions,
        user_answers=user_answers
    )

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

