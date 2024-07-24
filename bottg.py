import telebot
from telebot import types
import random
import logging
import requests
import sqlite3
import re
from dotenv import load_dotenv
import os

# Загрузка переменных из файла .env
load_dotenv()
TOKEN = os.getenv('TOKEN')
API_KEY = os.getenv('API_KEY')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
bot = telebot.TeleBot(TOKEN)

# Список интересных фактов о городе Жуковский
facts = [
    "Жуковский известен как центр авиации и космонавтики.",
    "Здесь находится Центральный аэрогидродинамический институт.",
    "Город носит имя известного авиаконструктора Николая Жуковского.",
    "Жуковский был основан в 1947 году как рабочий поселок.",
    "В городе ежегодно проводится международный авиационно-космический салон МАКС.",
    "Жуковский имеет одно из крупнейших авиационных кладбищ в России.",
    "В городе расположен крупнейший в Европе аэродром для испытательных полетов.",
    "Жуковский является важным научным центром в области аэродинамики.",
    "Город активно развивается в сфере высоких технологий и инноваций.",
    "Жуковский окружен красивыми лесами и природными зонами для отдыха."
]

# Создание основных кнопок
def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.KeyboardButton('Канал города Жуковский ✈️'),
        types.KeyboardButton('Форум 🏠'),
        types.KeyboardButton('Навигация по городу 🗺️'),
        types.KeyboardButton('Интересный факт 🗒️'),
        types.KeyboardButton('Текущая погода 🌤️'),
        types.KeyboardButton('События 🎉'),
    ]
    markup.add(*buttons)
    return markup

# Создание подменю
def create_submenu(buttons):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons:
        markup.add(types.KeyboardButton(button))
    return markup

# Создание инлайн-кнопок
def create_inline_submenu(buttons):
    markup = types.InlineKeyboardMarkup()
    for button_text, callback_data in buttons:
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
    return markup

# Функции работы с базой данных
def connect_db():
    try:
        conn = sqlite3.connect(r'E:\project\database\bazatg.db', timeout=20)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        raise

def initialize_db():
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS "users" (
                    "user_id" TEXT PRIMARY KEY,
                    "phone" TEXT NOT NULL,
                    "first_name" TEXT
                );
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")

def is_valid_phone(phone):
    return re.match(r'^\+?\d{10,15}$', phone)

# Состояния для регистрации
STATE_WAITING_FOR_CONSENT = 1
STATE_WAITING_FOR_PHONE = 2
STATE_WAITING_FOR_NAME = 3
user_states = {}

# Политика конфиденциальности
privacy_policy = (
    "*Политика конфиденциальности* 📜\n\n"
    "🔒 **Сбор данных:**\n"
    "Мы собираем ваш номер телефона для улучшения обслуживания.\n\n"
    "🔐 **Использование данных:**\n"
    "Данные используются только для обслуживания и не передаются третьим лицам.\n\n"
    "✅ **Согласие:**\n"
    "Нажмите 'Я согласен(а)' для продолжения.\n\n"
    "❌ **Отказ:**\n"
    "Нажмите 'Я не согласен(а)' для отказа. Функционал будет ограничен."
)

# Функция для создания клавиатуры с кнопками согласия и отказа
def create_consent_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    consent_button = types.KeyboardButton('Я согласен(а) предоставить данные')
    decline_button = types.KeyboardButton('Я не согласен(а)')
    markup.add(consent_button, decline_button)
    return markup

# Обработчик команды /start и /help
@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()

            if user is None:
                bot.send_message(
                    message.chat.id,
                    privacy_policy,
                    reply_markup=create_consent_keyboard()
                )
                user_states[user_id] = STATE_WAITING_FOR_CONSENT
            else:
                bot.send_message(message.chat.id, f'Привет, {user[2]}! На связи Жук-Навигатор.\n\nЖду твои пожелания по досугу, чтобы предложить варианты 💚', reply_markup=create_main_keyboard())
    except Exception as e:
        logging.error(f"Error in /start or /help handler: {e}")

# Обработка согласия или отказа пользователя
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == STATE_WAITING_FOR_CONSENT)
def handle_consent(message):
    if message.text == 'Я согласен(а) предоставить данные':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        phone_button = types.KeyboardButton('Отправить номер телефона', request_contact=True)
        markup.add(phone_button)
        bot.send_message(
            message.chat.id,
            "Спасибо за согласие! Пожалуйста, нажмите на кнопку ниже, чтобы отправить свой номер телефона.",
            reply_markup=markup
        )
        user_states[message.from_user.id] = STATE_WAITING_FOR_PHONE
    elif message.text == 'Я не согласен(а)':
        bot.send_message(
            message.chat.id,
            "Вы отказались предоставить номер телефона. Функционал бота будет ограничен!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        user_states[message.from_user.id] = STATE_WAITING_FOR_CONSENT
    else:
        bot.send_message(message.chat.id, "Для продолжения регистрации необходимо согласие на предоставление номера телефона.")

# Обработка сообщения с номером телефона
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    contact = message.contact

    if contact:
        phone = contact.phone_number

        if not is_valid_phone(phone):
            bot.send_message(message.chat.id, "Пожалуйста, отправьте корректный номер телефона.")
            return

        try:
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO users (user_id, phone) VALUES (?, ?)', (user_id, phone))
                conn.commit()

            bot.send_message(message.chat.id, "Отлично! Теперь скажите, как вас зовут?")
            user_states[user_id] = STATE_WAITING_FOR_NAME
        except Exception as e:
            logging.error(f"Error handling contact: {e}")

# Обработка имени
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == STATE_WAITING_FOR_NAME)
def handle_name(message):
    user_id = message.from_user.id
    first_name = message.text

    if not first_name.strip():
        bot.send_message(message.chat.id, "Имя не может быть пустым. Пожалуйста, введите ваше имя.")
        return

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET first_name = ? WHERE user_id = ?', (first_name, user_id))
            conn.commit()

        bot.send_message(message.chat.id, f"Спасибо за регистрацию, {first_name}!")
        del user_states[user_id]

        bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=create_main_keyboard())
    except Exception as e:
        logging.error(f"Error handling name: {e}")

# Обработчик основных кнопок
@bot.message_handler(func=lambda message: True)
def handle_main_buttons(message):
    if message.chat.type == 'private':
        try:
            text = message.text
            if text == 'Канал города Жуковский ✈️':
                bot.send_message(message.chat.id, 'Узнайте больше о городе, интересных местах и специальных предложениях в нашем канале!\nПодписывайтесь, чтобы получить скидку в кофейнях города!')
            elif text == 'Форум 🏠':
                submenu_buttons = ['Купить билет 🎟️', 'Зоны Форума 🏞️', 'Назад ◀️']
                bot.send_message(message.chat.id, 'Выберите действие на Форуме:', reply_markup=create_submenu(submenu_buttons))
                user_states[message.from_user.id] = 'forum_menu'
            elif text == 'Навигация по городу 🗺️':
                submenu_buttons = ['Где поесть 🍽️', 'Куда сходить 🚶‍♂️', 'Рядом со мной 📍', 'Назад ◀️']
                bot.send_message(message.chat.id, 'Выберите категорию навигации:', reply_markup=create_submenu(submenu_buttons))
                user_states[message.from_user.id] = 'navigation_menu'
            elif text == 'Интересный факт 🗒️':
                fact = random.choice(facts)
                bot.send_message(message.chat.id, f'Интересный факт о Жуковском:\n\n{fact}')
            elif text == 'Текущая погода 🌤️':
                weather = get_weather()
                bot.send_message(message.chat.id, f'Текущая погода в Жуковском:\n\n{weather}')
            elif text == 'События 🎉':
                events = get_events()
                bot.send_message(message.chat.id, f'Предстоящие события в Жуковском:\n\n{events}')
            # Подменю "Навигация по городу"
            elif text == 'Где поесть 🍽️':
                buttons = [('Кофейни', 'coffee_1'), ('Рестораны', 'restaurant_1')]
                bot.send_message(message.chat.id, 'Выберите место, где хотели бы поесть:', reply_markup=create_inline_submenu(buttons))
                user_states[message.from_user.id] = 'dining_menu'
            elif text == 'Куда сходить 🚶‍♂️':
                buttons = [('Природа', 'nature'), ('Архитектура', 'architecture'), ('История', 'history')]
                bot.send_message(message.chat.id, 'Выберите категорию мест, куда хотели бы сходить:', reply_markup=create_inline_submenu(buttons))
                user_states[message.from_user.id] = 'places_menu'
            elif text == 'Рядом со мной 📍':
                bot.send_message(message.chat.id, 'Мы всегда рядом с вами :)')
            # Подменю "Форум"
            elif text == 'Купить билет 🎟️':
                bot.send_message(message.chat.id, 'Здесь будет возможность купить билет')
            elif text == 'Зоны Форума 🏞️':
                buttons = [
                    ('Здоровый образ жизни', 'health'), 
                    ('Деловой ритм жизни', 'business'), 
                    ('Инфраструктура и транспорт', 'infrastructure'), 
                    ('Наука', 'science'), 
                    ('Досуг', 'leisure'), 
                    ('Молодежь и дети', 'youth'), 
                    ('Назад ◀️', 'back')
                ]
                bot.send_message(message.chat.id, 'Выберите интересующую вас зону:', reply_markup=create_inline_submenu(buttons))
                user_states[message.from_user.id] = 'forum_zones_menu'
            elif text == 'Назад ◀️':
                current_state = user_states.get(message.from_user.id)
                if current_state == 'forum_menu':
                    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=create_main_keyboard())
                elif current_state == 'navigation_menu':
                    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=create_main_keyboard())
                elif current_state == 'dining_menu':
                    bot.send_message(message.chat.id, 'Выберите категорию навигации:', reply_markup=create_submenu(['Где поесть 🍽️', 'Куда сходить 🚶‍♂️', 'Рядом со мной 📍', 'Назад ◀️']))
                elif current_state == 'places_menu':
                    bot.send_message(message.chat.id, 'Выберите категорию навигации:', reply_markup=create_submenu(['Где поесть 🍽️', 'Куда сходить 🚶‍♂️', 'Рядом со мной 📍', 'Назад ◀️']))
                elif current_state == 'forum_zones_menu':
                    bot.send_message(message.chat.id, 'Выберите действие на Форуме:', reply_markup=create_submenu(['Купить билет 🎟️', 'Зоны Форума 🏞️', 'Назад ◀️']))
                else:
                    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=create_main_keyboard())
                del user_states[message.from_user.id]
        except Exception as e:
            logging.error(f"Error handling button: {e}")

# Функция получения текущей погоды
def get_weather():
    city = 'Жуковский'
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather_description = data['weather'][0]['description']
        temperature = data['main']['temp']
        return f'{weather_description.capitalize()}, {temperature}°C'
    else:
        return 'Не удалось получить данные о погоде.'

# Функция получения предстоящих событий
def get_events():
    events = [
        "Авиационный салон МАКС - 20 июля 2024",
        "Фестиваль науки - 15 августа 2024",
        "Концерт в парке - 25 августа 2024"
    ]
    return "\n".join(events)

# Обработчик инлайн-кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        responses = {
            'health': ('https://i.postimg.cc/G20tQ8Wp/image.jpg', 'Зона «Здоровый образ жизни»'),
            'business': ('https://i.postimg.cc/nzkshVWc/image.jpg', 'Зона «Деловой ритм жизни»'),
            'infrastructure': ('https://i.postimg.cc/mg5JKQ2T/image.jpg', 'Зона «Инфраструктура и транспорт»'),
            'science': ('https://i.postimg.cc/wTxrvW16/image.jpg', 'Зона «Наука»'),
            'leisure': ('https://i.postimg.cc/9XbxvGJs/image.jpg', 'Зона «Досуг»'),
            'youth': ('https://i.postimg.cc/15YvzyxH/image.jpg', 'Зона «Молодежь и дети»'),
            'coffee_1': ('https://i.postimg.cc/HxMv7RgN/image.jpg', 'Уютная кофейня рядом с центральным сквером 🌳\n\n📍 ул. Маяковского, 9'),
            'restaurant_1': ('https://i.postimg.cc/gjShcc7b/image.jpg', 'Современное кафе прямо на набережной 🌊\n\n📍 ул. Федотова'),
            'nature': ('https://i.postimg.cc/qBhvvQXV/image.jpg', '🍃 Многовековые сосны и современное благоустройство: обновленный центральный парк города понравится каждому гостю.\n\n📍 ул. Комсомольская, 9'),
            'architecture': ('https://i.postimg.cc/d06LG1Db/image.jpg', '🏛️ Здание ДК, инженерный комплекс ЦАГИ, бульвары, жилые кварталы – гуляя по «старому» Жуковскому и рассматривая детали, вы станете знатоком особенностей советского конструктивистского стиля.\n\n📍 Пересечение улиц Фрунзе и Маяковского'),
            'history': ('https://i.postimg.cc/QtMVm3TH/image.jpg', '⛲️ От великолепной усадьбы Быково до наших дней сохранились дворец начала 19 века, пейзажный парк с прудами, а также потрясающая Владимирская церковь в неоготическом стиле.\n\n📍 Раменский г.о, пос. Быково')
        }
        
        if call.data in responses:
            image_url, caption = responses[call.data]
            bot.send_photo(call.message.chat.id, image_url, caption=caption)
    except Exception as e:
        logging.error(f"Error handling callback: {e}")

# Запуск бота
if __name__ == "__main__":
    try:
        logging.info("Starting bot...")
        initialize_db()
        bot.infinity_polling()
    except Exception as e:
        logging.critical(f"Failed to start bot: {e}")
