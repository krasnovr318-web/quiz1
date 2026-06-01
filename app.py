from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import string
from config import Config
from functools import wraps
import json
import hashlib

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Конфигурация админ-доступа (хеши для секретного слова и кода)
ADMIN_SECRET_WORD_HASH = 'cc4b8580b1c214cc3c3e204acc2c8ff62739baab0f981b84fee93cfed9a71a32'
ADMIN_ACCESS_CODE_HASH = '4cbc94725af76cc0347cd3ed31524a937d4182f3c83641d7d67d61b3959c1a96'


# Модели базы данных
class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Вот эту строку добавь
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quizzes = db.relationship('Quiz', backref='creator', lazy=True)
    quiz_plays = db.relationship('QuizPlay', backref='player', lazy=True)


class Quiz(db.Model):
    id = db.Column(db.String(12), primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    theme_color = db.Column(db.String(7), default='#808080')
    text_color = db.Column(db.String(7), default='#FFFFFF')
    button_color = db.Column(db.String(7), default='#A0A0A0')
    time_limit = db.Column(db.Integer, default=30)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    plays = db.relationship('QuizPlay', backref='quiz', lazy=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(12), db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Integer, nullable=False)
    answers = db.Column(db.Text, nullable=False)  # JSON строка с ответами


class QuizPlay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.String(12), db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)


class LikeDislike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.String(12), db.ForeignKey('quiz.id'), nullable=False)
    is_like = db.Column(db.Boolean, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Функции-помощники
def generate_id(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_code(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Необходимо войти в систему', 'error')
            return redirect(url_for('login'))

        if not current_user.is_admin:
            flash('Доступ запрещен. Только для администраторов.', 'error')
            return redirect(url_for('dashboard'))

        # Проверка, прошел ли админ двухфакторную проверку
        if not session.get('admin_verified'):
            return redirect(url_for('admin_verify'))

        return f(*args, **kwargs)

    return decorated_function


# Маршруты аутентификации
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Валидация пароля
        if len(password) < 8:
            flash('Пароль должен содержать не менее 8 символов', 'error')
            return render_template('register.html')

        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            flash('Пароль должен содержать буквы и цифры', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        # Проверка существующего пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('register.html')

        # Создание пользователя
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Успешный вход!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    # Очищаем сессию админа при выходе
    session.pop('admin_verified', None)
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# Основные маршруты
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/create-quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if request.method == 'POST':
        title = request.form.get('title')
        theme_color = request.form.get('theme_color', '#808080')
        text_color = request.form.get('text_color', '#FFFFFF')
        button_color = request.form.get('button_color', '#A0A0A0')
        time_limit = int(request.form.get('time_limit', 30))

        # Валидация времени
        if time_limit < 5 or time_limit > 3600:
            flash('Время должно быть от 5 секунд до 3600 секунд (60 минут)', 'error')
            return render_template('create_quiz.html')

        # Создание викторины
        quiz_id = generate_id()
        quiz_code = generate_code()

        quiz = Quiz(
            id=quiz_id,
            code=quiz_code,
            title=title,
            theme_color=theme_color,
            text_color=text_color,
            button_color=button_color,
            time_limit=time_limit,
            user_id=current_user.id
        )

        db.session.add(quiz)

        # Обработка вопросов
        question_count = int(request.form.get('question_count', 1))

        for i in range(question_count):
            question_text = request.form.get(f'question_{i}')
            correct_answer = int(request.form.get(f'correct_answer_{i}', 0))

            # Получение ответов
            answers = []
            answer_count = int(request.form.get(f'answer_count_{i}', 2))

            for j in range(answer_count):
                answer_text = request.form.get(f'answer_{i}_{j}')
                if answer_text:
                    answers.append(answer_text)

            if len(answers) < 2 or len(answers) > 10:
                flash(f'Вопрос {i + 1} должен содержать от 2 до 10 ответов', 'error')
                return render_template('create_quiz.html')

            question = Question(
                quiz_id=quiz_id,
                question_text=question_text,
                correct_answer=correct_answer,
                answers=json.dumps(answers)
            )

            db.session.add(question)

        db.session.commit()

        flash(f'Викторина создана! Код для входа: {quiz_code}', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_quiz.html')


@app.route('/join-quiz', methods=['GET', 'POST'])
@login_required
def join_quiz():
    if request.method == 'POST':
        code = request.form.get('code')

        quiz = Quiz.query.filter_by(code=code).first()

        if not quiz:
            flash('Викторина с таким кодом не найдена', 'error')
            return render_template('join_quiz.html')

        return redirect(url_for('play_quiz', quiz_id=quiz.id))

    return render_template('join_quiz.html')


@app.route('/quiz-list')
@login_required
def quiz_list():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'popular')

    if search:
        quizzes = Quiz.query.filter(
            (Quiz.title.contains(search)) | (Quiz.id.contains(search))
        ).all()
    else:
        quizzes = Quiz.query.all()

    if sort == 'popular':
        quizzes = sorted(quizzes, key=lambda q: q.likes, reverse=True)
    elif sort == 'recent':
        quizzes = sorted(quizzes, key=lambda q: q.created_at, reverse=True)

    return render_template('quiz_list.html', quizzes=quizzes)


@app.route('/play-quiz/<quiz_id>', methods=['GET', 'POST'])
@login_required
def play_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
        # Обработка результатов
        score = 0
        questions = Question.query.filter_by(quiz_id=quiz_id).all()

        for question in questions:
            user_answer = request.form.get(f'question_{question.id}')
            if user_answer and int(user_answer) == question.correct_answer:
                score += 1

        # Сохранение результата
        quiz_play = QuizPlay(
            user_id=current_user.id,
            quiz_id=quiz_id,
            score=score
        )

        db.session.add(quiz_play)
        db.session.commit()

        flash(f'Викторина пройдена! Ваш результат: {score}/{len(questions)}', 'success')
        return redirect(url_for('profile'))

    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return render_template('play_quiz.html', quiz=quiz, questions=questions)


@app.route('/like-quiz/<quiz_id>', methods=['POST'])
@login_required
def like_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Проверяем, не лайкал ли уже пользователь
    existing = LikeDislike.query.filter_by(
        user_id=current_user.id,
        quiz_id=quiz_id
    ).first()

    if existing:
        if existing.is_like:
            # Убираем лайк
            db.session.delete(existing)
            quiz.likes -= 1
        else:
            # Меняем дизлайк на лайк
            existing.is_like = True
            quiz.likes += 1
            quiz.dislikes -= 1
    else:
        # Ставим лайк
        like = LikeDislike(
            user_id=current_user.id,
            quiz_id=quiz_id,
            is_like=True
        )
        db.session.add(like)
        quiz.likes += 1

    db.session.commit()
    return jsonify({'likes': quiz.likes, 'dislikes': quiz.dislikes})


@app.route('/dislike-quiz/<quiz_id>', methods=['POST'])
@login_required
def dislike_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    existing = LikeDislike.query.filter_by(
        user_id=current_user.id,
        quiz_id=quiz_id
    ).first()

    if existing:
        if not existing.is_like:
            # Убираем дизлайк
            db.session.delete(existing)
            quiz.dislikes -= 1
        else:
            # Меняем лайк на дизлайк
            existing.is_like = False
            quiz.likes -= 1
            quiz.dislikes += 1
    else:
        # Ставим дизлайк
        like = LikeDislike(
            user_id=current_user.id,
            quiz_id=quiz_id,
            is_like=False
        )
        db.session.add(like)
        quiz.dislikes += 1

    db.session.commit()
    return jsonify({'likes': quiz.likes, 'dislikes': quiz.dislikes})


@app.route('/profile')
@login_required
def profile():
    user = current_user

    # Статистика
    total_likes = sum(quiz.likes for quiz in user.quizzes)
    total_dislikes = sum(quiz.dislikes for quiz in user.quizzes)
    quizzes_created = len(user.quizzes)
    quizzes_played = len(user.quiz_plays)

    # История последних 5 пройденных викторин
    recent_plays = QuizPlay.query.filter_by(user_id=user.id) \
        .order_by(QuizPlay.played_at.desc()).limit(5).all()

    # Созданные викторины
    created_quizzes = Quiz.query.filter_by(user_id=user.id).all()

    return render_template('profile.html',
                           user=user,
                           total_likes=total_likes,
                           total_dislikes=total_dislikes,
                           quizzes_created=quizzes_created,
                           quizzes_played=quizzes_played,
                           recent_plays=recent_plays,
                           created_quizzes=created_quizzes)


@app.route('/edit-quiz/<quiz_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Проверка прав
    if quiz.user_id != current_user.id and not current_user.is_admin:
        flash('У вас нет прав на редактирование этой викторины', 'error')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.theme_color = request.form.get('theme_color', quiz.theme_color)
        quiz.text_color = request.form.get('text_color', quiz.text_color)
        quiz.button_color = request.form.get('button_color', quiz.button_color)
        quiz.time_limit = int(request.form.get('time_limit', quiz.time_limit))

        # Удаление старых вопросов
        Question.query.filter_by(quiz_id=quiz_id).delete()

        # Добавление новых вопросов
        question_count = int(request.form.get('question_count', 1))

        for i in range(question_count):
            question_text = request.form.get(f'question_{i}')
            correct_answer = int(request.form.get(f'correct_answer_{i}', 0))

            answers = []
            answer_count = int(request.form.get(f'answer_count_{i}', 2))

            for j in range(answer_count):
                answer_text = request.form.get(f'answer_{i}_{j}')
                if answer_text:
                    answers.append(answer_text)

            question = Question(
                quiz_id=quiz_id,
                question_text=question_text,
                correct_answer=correct_answer,
                answers=json.dumps(answers)
            )

            db.session.add(question)

        db.session.commit()
        flash('Викторина обновлена!', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_quiz.html', quiz=quiz)


@app.route('/delete-quiz/<quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Проверка прав
    if quiz.user_id != current_user.id and not current_user.is_admin:
        flash('У вас нет прав на удаление этой викторины', 'error')
        return redirect(url_for('profile'))

    db.session.delete(quiz)
    db.session.commit()

    flash('Викторина удалена!', 'success')
    return redirect(url_for('profile'))


@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    password = request.form.get('password')

    if not check_password_hash(current_user.password_hash, password):
        flash('Неверный пароль', 'error')
        return redirect(url_for('profile'))

    user = User.query.get(current_user.id)

    # Удаление всех связанных данных
    LikeDislike.query.filter_by(user_id=user.id).delete()
    QuizPlay.query.filter_by(user_id=user.id).delete()

    # Удаление викторин пользователя
    for quiz in user.quizzes:
        db.session.delete(quiz)

    db.session.delete(user)
    db.session.commit()

    # Очищаем сессию админа
    session.pop('admin_verified', None)
    logout_user()
    flash('Аккаунт успешно удален', 'info')
    return redirect(url_for('index'))


# Админ-панель с двухфакторной защитой
@app.route('/admin/verify', methods=['GET', 'POST'])
@login_required
def admin_verify():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        secret_word = request.form.get('secret_word')
        access_code = request.form.get('access_code')

        # Проверяем секретное слово и код доступа
        secret_hash = hashlib.sha256(secret_word.encode()).hexdigest()
        code_hash = hashlib.sha256(access_code.encode()).hexdigest()

        if secret_hash == ADMIN_SECRET_WORD_HASH and code_hash == ADMIN_ACCESS_CODE_HASH:
            session['admin_verified'] = True
            flash('Доступ к админ-панели разрешен', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Неверное секретное слово или код доступа', 'error')

    return render_template('admin_verify.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    session.pop('admin_verified', None)
    flash('Вы вышли из админ-панели', 'info')
    return redirect(url_for('dashboard'))


@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = User.query.all()
    quizzes = Quiz.query.all()
    return render_template('admin.html', users=users, quizzes=quizzes)


@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash('Нельзя удалить администратора', 'error')
        return redirect(url_for('admin_panel'))

    # Удаление связанных данных
    LikeDislike.query.filter_by(user_id=user.id).delete()
    QuizPlay.query.filter_by(user_id=user.id).delete()

    for quiz in user.quizzes:
        db.session.delete(quiz)

    db.session.delete(user)
    db.session.commit()

    flash(f'Пользователь {user.username} удален', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete-quiz/<quiz_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()

    flash(f'Викторина {quiz.title} удалена', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/reset-all', methods=['POST'])
@login_required
@admin_required
def admin_reset_all():
    try:
        # Удаление всех данных
        LikeDislike.query.delete()
        QuizPlay.query.delete()
        Question.query.delete()
        Quiz.query.delete()

        # Удаление всех пользователей кроме админов
        User.query.filter_by(is_admin=False).delete()

        db.session.commit()
        flash('Все данные успешно сброшены', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при сбросе данных: {str(e)}', 'error')

    return redirect(url_for('admin_panel'))


# Создание админа (выполняется один раз)
def create_admin():
    with app.app_context():
        # Проверяем, используем ли мы SQLite (локально) или PostgreSQL (продакшн)
        is_sqlite = 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']

        if is_sqlite:
            db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@quiz.com',
                password_hash=generate_password_hash('Admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print('Администратор создан! Логин: admin, Пароль: Admin123')
            print('Секретное слово: кукуку')
            print('Код доступа: 12345678')


if __name__ == '__main__':
    create_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)