
from flask import Flask, render_template, session
from flask_wtf import FlaskForm
import hmac
from wtforms import StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import send_file
import logging
import datetime
import os
from flask import request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "blog"

# PostgreSQL configuration
app.config["POSTGRES_DB"] = "test_db"
app.config["POSTGRES_USER"] = "postgres"
app.config["POSTGRES_PASSWORD"] = "prosta4oklolkek"
app.config["POSTGRES_HOST"] = "localhost"
app.config["POSTGRES_PORT"] = "5432"

# Путь для хранения бекапов
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
UPLOAD_FOLDER1 = 'C:/Users/Ярослав/Desktop/BACK/'  # Путь для сохранения файлов
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Connect to PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        dbname=app.config["POSTGRES_DB"],
        user=app.config["POSTGRES_USER"],
        password=app.config["POSTGRES_PASSWORD"],
        host=app.config["POSTGRES_HOST"],
        port=app.config["POSTGRES_PORT"]
    )
    return conn

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Please login to view this page", "danger")
            return redirect(url_for("login"))

    return decorated_function


def get_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return user[0] if user else None

# User registration form
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[validators.Length(min=3, max=25)])
    username = StringField("Username", validators=[validators.Length(min=3, max=35)])
    email = StringField("Email", validators=[validators.Email(message="Please enter a valid email address")])
    password = PasswordField("Password", validators=[validators.DataRequired("Please enter a password"),
        validators.EqualTo(fieldname="confirm", message="Your password does not match")])
    confirm = PasswordField("Verify Password")

class LoginForm(FlaskForm):
    username = StringField("Username")
    password = PasswordField("Password")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/")
def index():
    return render_template("index.html")

@login_required
@app.route("/backups", methods=["GET", "POST"])
def view_backups():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":
        # Логика создания бекапа
        backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        backup_path = os.path.join(app.config['UPLOAD_FOLDER'], backup_name)

        # Здесь должна быть логика для создания бекапа.
        # Например, вы можете использовать shutil для копирования файлов в backup_path или создать пустой файл.
        with open(backup_path, 'w') as f:
            f.write("Бекап данных")  # Пример записи данных в файл

        # Запись информации о бекапе в базу данных
        cursor.execute("INSERT INTO backups (name, file_path, created_at) VALUES (%s, %s, NOW())",
                       (backup_name, backup_path))
        conn.commit()
        flash("Backup created successfully!", "success")

    # Запрос для извлечения всех необходимых данных из таблицы backups
    cursor.execute("SELECT id, name, created_at, file_path FROM backups;")
    backups = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("backups.html", backups=backups)


@login_required
@app.route("/backups/edit/<int:id>", methods=["GET", "POST"])
def edit_backup(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":
        # Обновляем данные бэкапа
        backup_name = request.form['backup_name']
        time = request.form['time']
        wal_file_name = request.form['wal_file_name']

        # Если загружен новый файл, сохраняем его
        if 'backup_file' in request.files:
            backup_file = request.files['backup_file']
            if backup_file.filename != '':
                backup_file.save(os.path.join(app.config['UPLOAD_FOLDER'], backup_file.filename))

        # Обновление записи в базе данных
        query = "UPDATE backups SET name = %s, created_at = %s WHERE id = %s"
        cursor.execute(query, (backup_name, time, id))
        conn.commit()

        flash("Бэкап обновлён успешно!", "success")
        return redirect(url_for("view_backups"))

    # Если метод GET, получаем данные текущего бэкапа для заполнения формы
    cursor.execute("SELECT * FROM backups WHERE id = %s", (id,))
    backup = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("edit_backup.html", backup=backup)


@app.route("/about")
def about():
    return render_template("about.html")

# Articles site
@app.route("/articles")
def articles():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM articles"
    cursor.execute(query)
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("articles.html", articles=articles)

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM articles WHERE author = %s"
    cursor.execute(query, (session["username"],))
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("dashboard.html", articles=articles)


# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.hash(form.password.data)

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)"
        cursor.execute(query, (name, email, username, password))
        conn.commit()
        cursor.close()
        conn.close()

        flash("You have successfully registered", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password_entered = request.form['password']

        # Получаем данные пользователя из базы данных
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and sha256_crypt.verify(password_entered, user['password']):
            flash("Вы успешно вошли в систему", "success")

            # Устанавливаем сессию
            session["logged_in"] = True
            session["username"] = username

            return redirect(url_for("index"))

        flash("Неверное имя пользователя или пароль", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")

# Detail page
@app.route("/article/<string:id>")
def article(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM articles WHERE id = %s"
    cursor.execute(query, (id,))
    article = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("article.html", article=article)

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully", "success")
    return redirect(url_for("index"))

@app.route('/backup_form')
@login_required
def backup_form():
    return render_template('backup_form.html')

@app.route('/submit_backup', methods=['POST'])
@login_required
def submit_backup():
    backup_name = request.form['backup_name']
    time = request.form['time']
    wal_file_name = request.form['wal_file_name']

    # Проверяем наличие загруженного файла
    if 'backup_file' not in request.files:
        flash("Файл бэкапа не выбран.", "danger")
        return redirect(url_for('backup_form'))

    backup_file = request.files['backup_file']

    if backup_file.filename == '':
        flash("Файл не выбран.", "danger")
        return redirect(url_for('backup_form'))

    # Сохраняем файл
    filename = secure_filename(backup_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    backup_file.save(file_path)

    # Добавляем запись в базу данных
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO backups (backup_name, time, wal_file_name, name, created_at, file_path)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (backup_name, time, wal_file_name, filename, datetime.now(), file_path))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Бэкап успешно добавлен!", "success")
    return redirect(url_for('view_backups'))

# Add article route
@app.route("/addarticle", methods=["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO articles(title, author, content) VALUES(%s, %s, %s)"
        cursor.execute(query, (title, session["username"], content))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Article successfully added", "success")
        return redirect(url_for("dashboard"))

    return render_template("addarticle.html", form=form)

@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM articles WHERE author = %s AND id = %s"
    cursor.execute(query, (session["username"], id))
    if cursor.fetchone():
        query2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(query2, (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))
    else:
        flash("There is no such article or you are not authorized for this action.")
        return redirect(url_for("index"))




# Путь к директории, где хранятся бекапы
BACKUP_DIRECTORY = '/path/to/your/backups'

logging.basicConfig(level=logging.DEBUG)


@app.route("/update_backup/<int:id>", methods=["POST"])
@login_required
def update_backup(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем данные из формы
    backup_name = request.form['backup_name']
    time = request.form['time']
    wal_file_name = request.form['wal_file_name']

    # Обработка файла, если он был загружен
    if 'backup_file' in request.files:
        backup_file = request.files['backup_file']
        if backup_file.filename != '':
            # Сохраняем новый файл бэкапа, если он был загружен
            backup_file.save(os.path.join('path/to/save', backup_file.filename))
            # Здесь ты можешь обновить путь к файлу в базе данных, если это необходимо

    # Обновляем бэкап в базе данных
    query = "UPDATE backups SET name = %s, time = %s, wal_file_name = %s WHERE id = %s"
    cursor.execute(query, (backup_name, time, wal_file_name, id))
    conn.commit()

    flash("Бэкап обновлён успешно!", "success")
    return redirect(url_for("backups_list"))

@app.route('/download/<int:id>', methods=['GET'])
@login_required
def download_backup(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT file_path FROM backups WHERE id = %s", (id,))
    backup = cursor.fetchone()
    cursor.close()
    conn.close()

    if backup is None or backup['file_path'] is None:
        print("Backup not found or path is not available.")
        flash("Backup not found or path is not available.", "danger")
        return redirect(url_for('view_backups'))

    file_path = backup['file_path']
    print(f"Attempting to download file from path: {file_path}")

    if not os.path.exists(file_path):
        print(f"File does not exist at path: {file_path}")
        flash("Backup file does not exist.", "danger")
        return redirect(url_for('view_backups'))

    return send_file(file_path, as_attachment=True)


@app.route('/delete_backup/<int:id>', methods=['POST'])
@login_required
def delete_backup(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем бекап из базы данных
    cursor.execute("DELETE FROM backups WHERE id = %s RETURNING id;", (id,))
    deleted_id = cursor.fetchone()

    conn.commit()
    cursor.close()
    conn.close()

    if deleted_id:
        flash("Backup successfully deleted", "success")
    else:
        flash("Backup not found", "danger")

    return redirect(url_for('view_backups'))


# Search URL
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = "SELECT * FROM articles WHERE title ILIKE %s"
        cursor.execute(query, ('%' + keyword + '%',))
        articles = cursor.fetchall()
        cursor.close()
        conn.close()
        if not articles:
            flash("No article found matching the search term", "warning")
            return redirect(url_for("articles"))
        return render_template("articles.html", articles=articles)

# Article form
class ArticleForm(FlaskForm):
    title = StringField("Title of Article", validators=[validators.Length(min=5, max=100)])
    content = TextAreaField("Content of Article", validators=[validators.Length(min=10)])

if __name__ == "__main__":
    app.run(debug=True)