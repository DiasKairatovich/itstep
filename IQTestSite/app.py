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
    {"id": 4, "question": "What is the largest planet in our solar system?", "options": ["Earth", "Jupiter", "Saturn"], "answer": "Jupiter"},
    {"id": 5, "question": "What is the chemical symbol for gold?", "options": ["Ag", "Au", "Pb"], "answer": "Au"},
    {"id": 6, "question": "Which ocean is the largest?", "options": ["Atlantic Ocean", "Indian Ocean", "Pacific Ocean"], "answer": "Pacific Ocean"},
    {"id": 7, "question": "Who wrote 'Romeo and Juliet'?", "options": ["William Shakespeare", "Charles Dickens", "Jane Austen"], "answer": "William Shakespeare"},
    {"id": 8, "question": "What is the fastest land animal?", "options": ["Cheetah", "Lion", "Horse"], "answer": "Cheetah"},
    {"id": 9, "question": "What is the currency of Japan?", "options": ["Yuan", "Yen", "Won"], "answer": "Yen"},
    {"id": 10, "question": "What is the chemical formula for water?", "options": ["H2O", "CO2", "O2"], "answer": "H2O"}
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
                # Insert new user into the database
                cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
                user_id = cursor.lastrowid
                conn.commit()

                # Log in the user immediately
                session['user_id'] = user_id
                flash("Registration successful! You are now logged in.", "success")
                return redirect(url_for("test"))
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

@app.route("/test", methods=["GET", "POST"])
def test():
    # Ensure the user is logged in
    user_id = session.get("user_id")
    if 'user_id' not in session:
        flash("Please log in to take the test.", "warning")
        return redirect(url_for("login"))

    # Initialize session variables for the test
    if 'current_question' not in session:
        session['current_question'] = 0
        session['answers'] = {}

    # Get the current question index
    current_question_index = session.get('current_question', 0)

    # If all questions are answered, redirect to results
    if current_question_index >= len(questions):
        return redirect(url_for("result"))

    # Get the current question based on the index
    current_question = questions[current_question_index]

    if request.method == "POST":
        # Collect the user's answer for the current question
        answer = request.form.get(str(current_question["id"]))
        if answer:
            session['answers'][str(current_question["id"])] = answer
            session['current_question'] += 1
        return redirect(url_for("test"))

    return render_template("test.html", question=current_question)



@app.route("/result")
def result():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("register"))

    # Retrieve answers from the session
    answers = session.get("answers", {})
    if not answers:
        flash("No answers found. Please retake the test.", "danger")
        return redirect(url_for("test"))

    # Save the answers to the database
    save_result(user_id, answers)

    # Clear answers and question index from the session
    session.pop("answers", None)
    session.pop("current_question", None)

    # Calculate the score
    score = sum(1 for question in questions if answers.get(str(question["id"])) == question["answer"])
    total_questions = len(questions)

    return render_template(
        "result.html",
        score=score,
        total_questions=total_questions,
        questions=questions,
        user_answers=answers
    )

def save_result(user_id, answers):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        # Convert answers dictionary to JSON
        answers_json = json.dumps(answers)
        cursor.execute("INSERT INTO results (user_id, answers) VALUES (?, ?)", (user_id, answers_json))
        conn.commit()

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

