from flask import Flask, render_template, request, redirect, url_for,send_from_directory,session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash,check_password_hash


from datetime import datetime

import sqlite3
import os


# расширения файлов, которые разрешено загружать
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__, template_folder='templates')
app.secret_key = "my_super_secret_key_123"

app.config['UPLOAD_FOLDER'] = 'uploads'
@app.route("/")
def task_list():
    # Подключение к базе данных
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    
    # Получение списка задач из базы данных
    cursor.execute('SELECT * FROM tasks')
    tasks = cursor.fetchall()
    
    # Закрытие соединения с базой данных
    conn.close()
    
    user_id = session.get("user_id")
    user_group = session.get("user_group")
    username = None  # Инициализация имени пользователя

    if user_id:
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()

        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        user_info = cursor.fetchone()

        if user_info:
            username = user_info[0]

        conn.close()

    return render_template("task_list.html", tasks=tasks, username=username, user_group=user_group)
from flask import request


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        selected_smena = request.form["smena"]

        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()

        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Выполнить запрос для получения задач в заданном диапазоне дат и смене
        cursor.execute('SELECT * FROM tasks WHERE due_date >= ? AND due_date <= ? AND smena = ?', (start_date, end_date, selected_smena))
        report_tasks = cursor.fetchall()

        task_images = {}
        for task in report_tasks:
            task_id = task[0]
            cursor.execute('SELECT filename FROM images WHERE task_id = ?', (task_id,))
            images = [image[0] for image in cursor.fetchall()]
            task_images[task_id] = images

        print(task_images)
        
        conn.close()

        return render_template("report.html", report_tasks=report_tasks, task_images=task_images)

    return render_template("report.html")




@app.route("/add", methods=["GET", "POST"])
def add_task():
    if request.method == "POST":
        # Получение данных из формы
        title = request.form["title"]
        description = request.form["description"]
        due_date = request.form["due_date"]
        smena = request.form["smena"]
        status = request.form["status"]
        
        # Подключение к базе данных
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        # Добавление задачи в базу данных
        cursor.execute('INSERT INTO tasks (title, description, due_date, smena, status, created_at) VALUES (?, ?, ?, ?, ?, datetime("now"))',
                       (title, description, due_date, smena, status))
                
        # Сохранение изменений и закрытие соединения с базой данных
        conn.commit()
        conn.close()
        
        # Перенаправление на главную страницу
        return redirect(url_for("task_list"))
    
    return render_template("add_task.html")



@app.route("/task/<int:task_id>", methods=["GET", "POST"])
def task_detail(task_id):
    # Подключение к базе данных
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    
    # Получение задачи по ID из базы данных
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    # Получение изображений, связанных с задачей, из базы данных
    cursor.execute('SELECT * FROM images WHERE task_id = ?', (task_id,))
    task_images = cursor.fetchall()
 
    
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")

        for uploaded_file in uploaded_files:
            if uploaded_file.filename != "":
                image_filename = secure_filename(uploaded_file.filename)
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
                uploaded_file.save(image_path)
                
                cursor.execute('INSERT INTO images (task_id, filename) VALUES (?, ?)', (task_id, image_filename))
                conn.commit()
        
        new_status = int(request.form["new_status"])
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', (new_status, task_id))
        conn.commit()
    
    # Закрытие соединения с базой данных
    conn.close()
    
    return render_template("task_detail.html", task=task, task_images=task_images)



@app.route("/task/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    cursor.execute('SELECT * FROM images WHERE task_id = ?', (task_id,))
    task_images = cursor.fetchall()
    
    task_due_date = task[8] if task[8] else ""
    
    if request.method == "POST":
        new_status = int(request.form["status"])
        new_due_date = request.form.get("due_date")  # Исправленная строка
        new_smena = int(request.form["smena"])
        
        if new_due_date:
            new_due_date = datetime.strptime(new_due_date, '%Y-%m-%d').date() 
        else:
            new_due_date = None

        cursor.execute('UPDATE tasks SET status = ?, due_date = ?, smena = ? WHERE id = ?', (new_status, new_due_date, new_smena, task_id))
        
        uploaded_files = request.files.getlist("images")
        new_title = request.form["title"]
        new_description = request.form["description"]
        delete_images = request.form.getlist("delete_images")
        new_comment = request.form["comment"]  

        for uploaded_file in uploaded_files:
            if uploaded_file.filename != "":
                image_filename = secure_filename(uploaded_file.filename)
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
                uploaded_file.save(image_path)

                cursor.execute('INSERT INTO images (task_id, filename) VALUES (?, ?)', (task_id, image_filename))

        # Удаление изображений
        for image_id in delete_images:
            cursor.execute('SELECT filename FROM images WHERE id = ?', (image_id,))
            image_record = cursor.fetchone()

            if image_record:
                image_filename = image_record[0]
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)

                if os.path.exists(image_path):
                    os.remove(image_path)
                cursor.execute('DELETE FROM images WHERE id = ?', (image_id,))  # Удаление изображения из базы данных
        
        cursor.execute('UPDATE tasks SET title = ?, description = ?, comment = ?, updated_at = datetime("now") WHERE id = ?', (new_title, new_description, new_comment, task_id))
        conn.commit()

        task = (*task[:3], new_title, new_description, new_comment)
        conn.close()

        return redirect(url_for("task_list"))

    conn.close()
    return render_template("edit_task.html", task=task, task_images=task_images, task_due_date=task_due_date)


@app.route("/edit_comment/<int:task_id>", methods=["POST"])
def edit_comment(task_id):
    if request.method == "POST":
        new_comment = request.form["comment"]
        
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        cursor.execute('UPDATE tasks SET comment = ? WHERE id = ?', (new_comment, task_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for("task_detail", task_id=task_id))
@app.route("/upload_images/<int:task_id>", methods=["POST"])
def upload_images(task_id):
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        
        for uploaded_file in uploaded_files:
            if uploaded_file.filename != "":
                image_filename = secure_filename(uploaded_file.filename)
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
                uploaded_file.save(image_path)
                
                conn = sqlite3.connect('tasks.db')
                cursor = conn.cursor()
                
                cursor.execute('INSERT INTO images (task_id, filename) VALUES (?, ?)', (task_id, image_filename))
                
                conn.commit()
                conn.close()
        
        return redirect(url_for("task_detail", task_id=task_id))

@app.route("/task/<int:task_id>/edit_comment", methods=["GET"])
def show_edit_comment(task_id):
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()

    conn.close()

    return render_template("edit_comment.html", task=task)

@app.route("/change_task_status/<int:task_id>", methods=["POST"])
def change_task_status(task_id):
    if request.method == "POST":
        new_status = int(request.form["new_status"])
        
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', (new_status, task_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for("task_detail", task_id=task_id))


@app.route("/uploads/<filename>")
def uploaded_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_group = request.form["user_group"] 
        
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO users (username, password, user_group) VALUES (?, ?, ?)', (username, hashed_password, user_group))
        conn.commit()
        conn.close()
        
        return redirect(url_for("login"))  
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None  # Инициализация переменной error

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and user[2]== password:
            # Успешная аутентификация, сохранение данных пользователя в сессии
            session["user_id"] = user[0]
            session["user_group"] = user[3]  # Сохранение группы в сессии
            return redirect(url_for("task_list"))
        else:
            error = "Неверные учетные данные. Пожалуйста, проверьте ваш логин и пароль."
        
        conn.close()
    
    return render_template("login.html", error=error)  # Передача переменной error в шаблон










@app.route("/user_list")
def user_list():

    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    
    conn.close()

    
    return render_template("user_list.html", users=users)


@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        # Получите данные из формы и добавьте пользователя в базу данных
        username = request.form["username"]
        password = request.form["password"]
        user_group = request.form["user_group"]
        
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO users (username, password, user_group) VALUES (?, ?, ?)',
                       (username, password, user_group))
        
        conn.commit()
        conn.close()
        
        # Перенаправьте на страницу со списком пользователей после добавления
        return redirect(url_for("user_list"))
    
    return render_template("add_user.html")

@app.route("/logout")
def logout():
    # Удаляем данные пользователя из сессии
    session.pop("user_id", None)
    session.pop("user_group", None)
    return redirect(url_for("task_list"))

if  __name__== "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)