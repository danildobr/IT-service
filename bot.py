import os
import time
from telebot import TeleBot, types
from models import (Session, create_tables, engine, get_or_create_user,
                    add_category, Category)
from config import *
from keyboards import*


# Инициализация бота
bot = TeleBot(TOKEN)

# with Session() as session:
#     # create_tables(engine)
#     add_category(session)
    
@bot.message_handler(commands=['start'])
def send_welcome(message):
    with Session() as session:
        user = get_or_create_user(session, message)

    if user:
        bot.send_message(message.chat.id, f'Добро пожаловать, {message.from_user.username}!\n'
                'Используйте /ticket для создания новой заявки.')       
    else:
        bot.send_message(message.chat.id, "Ошибка в добавление пользователя")
        
        

@bot.message_handler(commands=['ticket'])
def create_ticket(message):
    with Session() as session:
        categories = session.query(Category).all()

    if not categories:
        bot.send_message(message.chat.id, "К сожалению, категории ещё не загружены.")
        return 

    # Создаём клавиатуру
    keyboard = keyboard_category(categories)

    bot.send_message(message.chat.id, "Выберите категорию проблемы:",
        reply_markup=keyboard)

# Обработка выбора категории
@bot.message_handler(func=lambda message: message.text in get_all_category_names() or message.text == "Отмена")
def show_advice(message):
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Создание заявки отменено.",
            reply_markup=types.ReplyKeyboardRemove())
        return

    with Session() as session:
        category = session.query(Category).filter_by(name=message.text).first()

    if category:
        bot.send_message(
            message.chat.id,
            f"🔧 <b>Категория:</b> {category.name}\n\n"
            f"📘 <b>Рекомендации:</b>\n{category.advice}",
            parse_mode='HTML',
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        bot.send_message(message.chat.id, "Категория не найдена.")

# Вспомогательная функция: получить все названия категорий
def get_all_category_names():
    with Session() as session:
        return [cat.name for cat in session.query(Category).all()]
    
    

    
    
    
    
if __name__ == '__main__':
    '''Запуск бота'''
    for i in range(3, 0, -1):
        print(f'{i}...')
        time.sleep(0.5)
    bot.polling()