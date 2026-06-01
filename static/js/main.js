// Общие функции для всего сайта

// Автоматическое скрытие alert-сообщений через 5 секунд
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Валидация пароля при регистрации
function validatePassword(password) {
    const minLength = 8;
    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumber = /\d/.test(password);

    if (password.length < minLength) {
        return 'Пароль должен содержать минимум 8 символов';
    }

    if (!hasLetter || !hasNumber) {
        return 'Пароль должен содержать буквы и цифры';
    }

    return null;
}

// Подтверждение действий
function confirmAction(message) {
    return confirm(message || 'Вы уверены?');
}

// Форматирование даты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Копирование текста в буфер обмена
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Скопировано в буфер обмена!');
    }).catch(err => {
        console.error('Ошибка копирования:', err);
    });
}

// Анимация загрузки
function showLoading(element) {
    element.innerHTML = '<div class="spinner-border text-light" role="status"><span class="visually-hidden">Загрузка...</span></div>';
}

function hideLoading(element, originalContent) {
    element.innerHTML = originalContent;
}

// Обработка ошибок fetch
function handleFetchError(error) {
    console.error('Ошибка:', error);
    alert('Произошла ошибка. Попробуйте позже.');
}

// Динамическое обновление лайков/дизлайков
function setupLikeDislikeButtons() {
    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const quizId = this.dataset.quizId;
            try {
                const response = await fetch(`/like-quiz/${quizId}`, { method: 'POST' });
                const data = await response.json();
                updateLikeDislikeCounts(this.closest('.card-body'), data);
            } catch (error) {
                handleFetchError(error);
            }
        });
    });

    document.querySelectorAll('.dislike-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const quizId = this.dataset.quizId;
            try {
                const response = await fetch(`/dislike-quiz/${quizId}`, { method: 'POST' });
                const data = await response.json();
                updateLikeDislikeCounts(this.closest('.card-body'), data);
            } catch (error) {
                handleFetchError(error);
            }
        });
    });
}

function updateLikeDislikeCounts(container, data) {
    const likesElement = container.querySelector('.likes-count');
    const dislikesElement = container.querySelector('.dislikes-count');

    if (likesElement) likesElement.textContent = data.likes;
    if (dislikesElement) dislikesElement.textContent = data.dislikes;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    setupLikeDislikeButtons();
});