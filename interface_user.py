import os
import time
from telebot import TeleBot, types
from models import (Session, engine, Category)
from config import *
from keyboards import *
from working_db import * 
import uuid


# Инициализация бота
bot = TeleBot(TOKEN)

# настройка БД: 1-создание таблиц
                # 2-заполенеие БД
                # 3-добавление ИТ специалистов в БД
# with Session() as session:
#     create_tables(engine)
#     add_category(session)
    # setup_it_specialists()
    
    
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    with Session() as session:
        user = get_or_create_user(session, message)
        
    if user:
        bot.send_message(
            message.chat.id,
            f"👋 Добро пожаловать, {message.from_user.first_name}!\n"
            "📌 Используйте /ticket для создания новой заявки.\n"
            "📊 Используйте /status для просмотра ваших заявок.",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        bot.send_message(message.chat.id, "⚠️ Ошибка при регистрации. Попробуйте позже.")
        

@bot.message_handler(commands=['ticket'])
def create_ticket(message):
    """Начало создания заявки - выбор категории"""
    with Session() as session:
        categories = session.query(Category).all()
    try:
        if not categories:
            bot.send_message(message.chat.id, "⚠️ Категории проблем пока не загружены.")
            return
        
        markup = types.InlineKeyboardMarkup()
        for category in categories:
            markup.add(types.InlineKeyboardButton(text=category.name,
                callback_data=f"category_{category.id}"))
        
        bot.send_message(message.chat.id, "🛠 Выберите категорию проблемы:",
            reply_markup=markup)
        
    except Exception as e:
        print(f'ошибка в функции create_ticket: {e} ')

@bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
def handle_category_selection(call):
    """Обработка выбора категории"""
    category_id = int(call.data.split('_')[1])
    
    with Session() as session:
        category = session.get(Category, category_id)
        if not category or not category.subcategories:
            bot.answer_callback_query(call.id, "Категория не найдена!")
            return
        
        # Создаем клавиатуру с подкатегориями
        markup = types.InlineKeyboardMarkup()
        for subcat in category.subcategories:
            markup.add(types.InlineKeyboardButton(
                text=subcat.name,
                callback_data=f"subcat_{subcat.id}"
            ))
        
        bot.edit_message_text(
            f"📂 Категория: {category.name}\n"
            "Выберите подкатегорию:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('subcat_'))
def handle_subcategory_selection(call):
    """Обработка выбора подкатегории"""
    subcat_id = int(call.data.split('_')[1])
    
    with Session() as session:
        subcat = session.get(Subcategory, subcat_id)
        if not subcat:
            bot.answer_callback_query(call.id, "Подкатегория не найдена!")
            return
        
        # Сохраняем subcat_id в данных пользователя
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            f"🔧 <b>{subcat.category.name} → {subcat.name}</b>\n\n"
            f"📝 <b>Рекомендация:</b>\n{subcat.recommendation}\n\n"
            "Помогли ли эти рекомендации?",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
        # Создаем клавиатуру с вариантами ответа
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Помогло", callback_data=f"help_yes_{subcat.id}"),
            types.InlineKeyboardButton("❌ Не помогло", callback_data=f"help_no_{subcat.id}")
        )
        
        bot.send_message(
            call.message.chat.id,
            "Выберите действие:",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('help_'))
def handle_help_response(call):
    """Обработка ответа на рекомендации"""
    action, subcat_id = call.data.split('_')[1], int(call.data.split('_')[2])
    
    if action == 'yes':
        # Если помогло - создаем закрытую заявку
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=call.from_user.id).first()
            subcat = session.get(Subcategory, subcat_id)
            
            if user and subcat:
                ticket = Ticket(
                    user_id=user.id,
                    subcategory_id=subcat.id,
                    status='Закрыт',
                    helped=True
                )
                session.add(ticket)
                session.commit()
                
                bot.edit_message_text(
                    "✅ Отлично, что рекомендации помогли!\n"
                    f"Заявка #{ticket.id} создана и закрыта.\n"
                    "Если проблема повторится, создайте новую заявку.",
                    call.message.chat.id,
                    call.message.message_id
                )
            else:
                bot.answer_callback_query(call.id, "Ошибка при создании заявки!")
    else:
        # Если не помогло - запрашиваем описание проблемы
        msg = bot.edit_message_text(
            "📝 Опишите проблему подробно:\n"
            "(Вы можете прикрепить скриншот)",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Сохраняем subcat_id для следующего шага
        bot.register_next_step_handler(
            msg, 
            process_problem_description, 
            subcat_id=subcat_id
        )


def process_problem_description(message, subcat_id):
    """Обработка описания проблемы и файлов"""
    # Проверяем, есть ли файл
    file_path = None
    file_info_text = ""
    
    if message.content_type == 'photo':
        # Обработка фото
        file_info = bot.get_file(message.photo[-1].file_id)
        file_ext = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'jpg'
        file_path = f"files/{uuid.uuid4()}.{file_ext}"
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        file_info_text = "\n📎 Прикреплено фото"
        
    elif message.document:
        # Проверяем размер файла
        if message.document.file_size > 10 * 1024 * 1024:  # 10 МБ
            bot.send_message(message.chat.id, "⚠️ Файл слишком большой (макс. 10 МБ)")
            return
        
        # Обработка документа
        file_info = bot.get_file(message.document.file_id)
        file_ext = message.document.file_name.split('.')[-1]
        file_path = f"files/{uuid.uuid4()}.{file_ext}"
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        file_info_text = f"\n📎 Прикреплен файл: {message.document.file_name}"
    
    # Получаем текст описания
    problem_description = message.text if message.content_type == 'text' else message.caption
    if not problem_description:
        problem_description = "Описание не указано"
    
    # Сохраняем заявку
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        subcat = session.get(Subcategory, subcat_id)
        
        if user and subcat:
            ticket = Ticket(
                user_id=user.id,
                subcategory_id=subcat.id,
                description=problem_description,
                status='Открыт',
                file_path=file_path,
                helped=False
            )
            session.add(ticket)
            session.commit()
            
            # Уведомление пользователя
            bot.send_message(
                message.chat.id,
                f"✅ Заявка #{ticket.id} создана!\n"
                f"Категория: {subcat.category.name} → {subcat.name}\n"
                f"Статус: Открыт\n"
                f"Ваше описание: {problem_description}{file_info_text}\n\n"
                "Вы можете проверить статус заявки с помощью /status.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Уведомление IT-специалистов
            notify_it_specialists(
                ticket_id=ticket.id,
                category_name=f"{subcat.category.name} → {subcat.name}",
                username=user.username,
                description=problem_description,
                file_info=file_info_text,
                created_at=ticket.created_at.strftime('%d.%m.%Y %H:%M')
            )
            
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ Ошибка при создании заявки. Попробуйте позже.",
                reply_markup=types.ReplyKeyboardRemove()
            )

def notify_it_specialists(ticket_id, category_name, username, description, file_info, created_at):
    """Отправляет уведомления IT-специалистам о новой заявке"""
    with Session() as session:
        it_specialists = session.query(User).filter_by(is_it_specialist=True).all()
        
        if not it_specialists:
            print("Нет IT-специалистов для уведомления")
            return
        
        message_text = (
            f"🚨 Новая заявка #{ticket_id}\n"
            f"👤 Пользователь: @{username}\n"
            f"📂 Категория: {category_name}\n"
            f"📝 Описание: {description}{file_info}\n"
            f"🕒 Время создания: {created_at}\n\n"
            f"Для взятия в работу: /take_{ticket_id}"
        )
        
        for specialist in it_specialists:
            try:
                bot.send_message(
                    specialist.telegram_id,
                    message_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления IT-специалисту {specialist.telegram_id}: {e}")


@bot.message_handler(commands=['status'])
def show_user_tickets(message):
    """Показывает заявки пользователя"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            bot.send_message(message.chat.id, "⚠️ Пользователь не найден")
            return
        
        tickets = session.query(Ticket).filter_by(user_id=user.id)\
            .order_by(Ticket.created_at.desc()).limit(10).all()
        
        if not tickets:
            bot.send_message(message.chat.id, "У вас пока нет заявок.")
            return
        
        response = "📋 Ваши последние заявки:\n\n"
        for ticket in tickets:
            # Добавляем цветовые индикаторы
            status_color = "🟢" if ticket.status == "Закрыт" else "🟡"
            if ticket.status == "В работе":
                status_color = "🟠"
            elif ticket.status == "Ожидает уточнений":
                status_color = "🔵"
            
            response += (
                f"🔹 #{ticket.id}\n"
                f"Категория: {ticket.subcategory.category.name} → {ticket.subcategory.name}\n"
                f"Статус: {status_color} {ticket.status}\n"  # Вот здесь применяем
                f"Дата: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )
            if ticket.closed_at:
                response += f"Закрыта: {ticket.closed_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += "\n"
        
        bot.send_message(message.chat.id, response)

        
        
        
        

    

    
    
    
    
if __name__ == '__main__':
    '''Запуск бота'''
    for i in range(3, 0, -1):
        print(f'{i}...')
        time.sleep(0.5)
    bot.polling()