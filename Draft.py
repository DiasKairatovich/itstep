import psycopg2

conn = psycopg2.connect(
    dbname="check_backup",
    user="dias",
    password="DunkBall17!",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

def create_data(name):
    cursor.execute(
        "INSERT INTO test_backup (name) VALUES (%s)",
        (name,)
    )
    conn.commit()
    print(f"Добавлено имя: {name}")

def delete_data(id):
    cursor.execute(
        "DELETE FROM test_backup WHERE id = %s",
        (id,)
    )
    conn.commit()
    print(f"Удалены данные по аиди: {id}")

def update_data(id, new_name):
    cursor.execute(
        "UPDATE test_backup SET name = %s WHERE id = %s",
        (new_name, id)
    )
    conn.commit()
    print(f"Обновлено имя пользователя с аиди: {id}")

def get_all_data():
    cursor.execute("SELECT * FROM test_backup")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

if __name__ == "__main__":
    # Для создания данных
    create_data("New_user")

    # Для редактирования данных
    update_data(3, "John")

    # Для удаления данных
    delete_data(2)

    # Для получения данных
    get_all_data()

    cursor.close()
    conn.close()