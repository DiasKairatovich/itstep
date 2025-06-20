import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="DunkBall17!",
    host="localhost",
    port="5432"
)
conn.autocommit = True
cursor = conn.cursor()

def create_user(name):
    cursor.execute("INSERT INTO users (name) VALUES (%s) RETURNING id;", (name,))
    user_id = cursor.fetchone()[0]
    print(f"Пользователь создан с id={user_id}")


def create_journal(title):
    cursor.execute("INSERT INTO journals (title) VALUES (%s) RETURNING id;", (title,))
    journal_id = cursor.fetchone()[0]
    print(f"Журнал создан с id={journal_id}")

def subscribe(user_id, journal_id):
    try:
        cursor.execute("INSERT INTO subscriptions (user_id, journal_id) VALUES (%s, %s);", (user_id, journal_id))
        print("Подписка добавлена.")
    except psycopg2.errors.UniqueViolation:
        print("Пользователь уже подписан!")
        conn.rollback()


def unsubscribe(user_id, journal_id):
    cursor.execute("DELETE FROM subscriptions WHERE user_id = %s AND journal_id = %s;", (user_id, journal_id))
    print("Подписка удалена!")


def show_all_info():
    cursor.execute("""
        SELECT u.name, j.title
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        JOIN journals j ON j.id = s.journal_id
        ORDER BY u.name;
    """)
    rows = cursor.fetchall()
    print("Текущие подписки:")
    for row in rows:
        print(f" - {row[0]} подписан на {row[1]}")
