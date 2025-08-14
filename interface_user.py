import html
import os
import time
from telebot import TeleBot, types
from models import (Session, engine, Category)
from config import *
from working_db import * 
import uuid
from interface_IT_specialist import *


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
        
        message_html = (
            f"<b>Новая заявка</b> #{ticket_id}\n"
            f"<b>Пользователь</b>: @{username}\n"
            f"<b>Категория</b>: {html.escape(category_name)}\n"
            f"<b>Описание</b>: {html.escape(description)}\n"
            f"{file_info}\n"
            f"<b>Время создания</b>: {created_at}\n\n"
            f"Для взятия в работу отправте сообщение: /take {ticket_id}")
        
        for specialist in it_specialists:
            try:
                bot.send_message(
                    chat_id=specialist.telegram_id,
                    text=message_html,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления IT-специалисту {specialist.telegram_id}: {str(e)[:200]}")  # Обрезаем длинные сообщения

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

        
        
        
        
        
        
        
        
        

# Добавляем в начало файла
IT_SPECIALIST_COMMANDS = ['take', 'close', 'mytickets', 'request_info', 'alltickets']



@bot.message_handler(commands=IT_SPECIALIST_COMMANDS)
def check_it_specialist(message):
    """Проверка прав IT-специалиста"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.is_it_specialist:
            bot.reply_to(message, "⛔ У вас нет прав для выполнения этой команды")
            return
    
    # Перенаправляем на соответствующие обработчики
    if message.text.startswith('/take'):
        take_ticket(message)
    elif message.text.startswith('/close'):
        close_ticket(message)
    elif message.text.startswith('/mytickets'):
        show_my_tickets(message)
    elif message.text.startswith('/request_info'):
        request_additional_info(message)
    elif message.text.startswith('/alltickets'):
        show_all_tickets(message)
        # список всех завок

def show_all_tickets(message):
    '''Получаем все заявки'''
            
    with Session() as session:

        tickets = session.query(Ticket).order_by(Ticket.created_at.desc()).all()

        if not tickets:
            bot.reply_to(message, "📭 Нет заявок в системе")
            return

        # Формируем части сообщения
        message_parts = []
        current_part = "📋 <b>Все заявки</b>:\n\n"
        
        for ticket in tickets:
            try:
                # Формируем информацию о заявке
                status_icon = {
                    'Открыт': '🟡',
                    'В работе': '🟠',
                    'Закрыт': '🟢',
                    'Ожидает уточнений': '🔵'
                }.get(ticket.status, '⚪')

                description = ticket.description if ticket.description else "нет описания"
                if len(description) > 100:
                    description = description[:100] + "..."

                ticket_info = (
                    f"{status_icon} <b>Заявка #{ticket.id}</b>\n"
                    f"👤 Пользователь: @{ticket.user.username}\n"
                    f"📌 Категория: {ticket.subcategory.category.name} → {ticket.subcategory.name}\n"
                    f"🕒 Создана: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"📝 Описание: {description}\n"
                    f"🔍 Статус: {ticket.status}\n"
                    f"🔹 /take_{ticket.id} /close_{ticket.id}\n\n"
                )

                # Проверяем, не превысит ли добавление новой заявки лимит
                if len(current_part) + len(ticket_info) > 4000:
                    message_parts.append(current_part)
                    current_part = ticket_info
                else:
                    current_part += ticket_info

            except Exception as e:
                print(f"Ошибка при обработке заявки {ticket.id}: {e}")
                continue

        # Добавляем последнюю часть
        if current_part:
            message_parts.append(current_part)

        # Отправляем сообщения
        for i, part in enumerate(message_parts, 1):
            try:
                # Для последней части добавляем общее количество
                if i == len(message_parts):
                    part += f"\nВсего заявок: {len(tickets)}"
                
                bot.send_message(
                    message.chat.id,
                    part,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Ошибка при отправке части сообщения: {e}")
        
def take_ticket(message):
    """Взять заявку в работу"""
    try:
        ticket_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Использование: /take <номер_заявки>")
        return
    
    with Session() as session:
        ticket = session.query(Ticket).filter_by(id=ticket_id, status='Открыт').first()
        if not ticket:
            bot.reply_to(message, "❌ Заявка не найдена или уже взята в работу")
            return
        
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        ticket.status = 'В работе'
        ticket.taken_at = datetime.now()
        session.commit()
        
        # Уведомление пользователя
        try:
            bot.send_message(
                ticket.user.telegram_id,
                f"🔄 Ваша заявка #{ticket.id} взята в работу\n"
                f"Категория: {ticket.subcategory.category.name}\n"
                f"Исполнитель: @{user.username}"
            )
        except Exception as e:
            print(f"Ошибка уведомления пользователя: {e}")
        
        bot.reply_to(message, f"✅ Вы взяли заявку #{ticket.id} в работу")

def close_ticket(message):
    """Закрыть заявку"""
    try:
        ticket_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Использование: /close <номер_заявки>")
        return
    
    with Session() as session:
        ticket = session.query(Ticket).filter_by(
            id=ticket_id, 
            status='В работе'
        ).first()
        
        if not ticket:
            bot.reply_to(message, "❌ Заявка не найдена или не в работе")
            return
        
        ticket.status = 'Закрыт'
        ticket.closed_at = datetime.now()
        session.commit()
        
        # Расчет времени выполнения
        time_spent = (ticket.closed_at - ticket.taken_at).total_seconds() / 60
        
        # Уведомление пользователя
        try:
            bot.send_message(
                ticket.user.telegram_id,
                f"✅ Ваша заявка #{ticket.id} закрыта\n"
                f"Время решения: {int(time_spent)} минут\n"
                f"Категория: {ticket.subcategory.category.name}"
            )
        except Exception as e:
            print(f"Ошибка уведомления пользователя: {e}")
        
        bot.reply_to(message, f"✅ Заявка #{ticket.id} закрыта. Время выполнения: {int(time_spent)} мин")

def show_my_tickets(message):
    """Показать заявки в работе у специалиста"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        tickets = session.query(Ticket).filter(
            Ticket.status == 'В работе'
        ).order_by(Ticket.taken_at.desc()).all()
        
        if not tickets:
            bot.reply_to(message, "У вас нет заявок в работе")
            return
        
        response = "📌 Ваши текущие заявки:\n\n"
        for ticket in tickets:
            time_in_work = (datetime.now() - ticket.taken_at).total_seconds() / 60
            response += (
                f"🔹 #{ticket.id}\n"
                f"Категория: {ticket.subcategory.category.name}\n"
                f"Пользователь: @{ticket.user.username}\n"
                f"В работе: {int(time_in_work)} мин\n"
                f"Описание: {ticket.description}\n"
                f"Дата: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            )
        
        bot.reply_to(message, response)

def request_additional_info(message):
    """Запросить дополнительную информацию"""
    try:
        ticket_id = int(message.text.split()[1])
        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).first()
            if not ticket:
                bot.reply_to(message, "❌ Заявка не найдена")
                return
            
            msg = bot.reply_to(message, 
                f"✏️ Введите запрос дополнительной информации по заявке #{ticket_id}:\n"
                "(Пользователь получит это сообщение)")
            
            bot.register_next_step_handler(msg, process_info_request, ticket_id)
            
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Использование: /request_info <номер_заявки>")

def process_info_request(message, ticket_id):
    """Обработка запроса информации"""
    with Session() as session:
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()
        if not ticket:
            bot.reply_to(message, "❌ Заявка не найдена")
            return
        
        ticket.status = 'Ожидает уточнений'
        session.commit()
        
        # Отправляем запрос пользователю
        try:
            bot.send_message(
                ticket.user.telegram_id,
                f"ℹ️ По вашей заявке #{ticket.id} требуется дополнительная информация:\n\n"
                f"{message.text}\n\n"
                f"Пожалуйста, ответьте на это сообщение"
            )
            bot.reply_to(message, f"✅ Запрос отправлен пользователю @{ticket.user.username}")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка отправки запроса: {e}")        
        

    

    
    
    
    
if __name__ == '__main__':
    '''Запуск бота'''
    for i in range(3, 0, -1):
        print(f'{i}...')
        time.sleep(0.5)
    bot.polling()