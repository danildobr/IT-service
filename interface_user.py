import html
from telebot import  types
from models import (Session, Category)
from config import *
from working_db import * 
from interface_IT_specialist import *



def register_user_handlers(bot):
    
    
    def get_user_keyboard(is_admin=False, is_it_specialist=False):
        """Возвращает клавиатуру в зависимости от роли"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        if is_admin:
            markup.add("📊 Статистика", "👥 Пользователи")
            markup.add("🛠 Управление ИТ-специалистами", )
            markup.add("📋 Загрузить категории")
            markup.add("Скачать файл с категориями")
        elif is_it_specialist:
            markup.add("📋 Все заявки", "✅ Закрыть заявку")
            markup.add("Запросить дополнительную информацию")
        else:
            markup.add("🆕 Новая заявка", "📋 Мои заявки")
        return markup
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        with Session() as session:
            user = get_or_create_user(session, message)
            markup = get_user_keyboard(user.is_admin, user.is_it_specialist)
            text = (
                "👑 Панель администратора" if user.is_admin else
                "👨‍💻 Панель ИТ-специалиста" if user.is_it_specialist else
                "👋 Добро пожаловать в систему поддержки"
            )
            bot.send_message(message.chat.id, f"{text}\nВыберите действие:", reply_markup=markup)
    
            
    @bot.message_handler(func=lambda msg: msg.text == "🆕 Новая заявка")
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
                # parse_mode='HTML'
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
                        status='Закрыта',
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
        """Обработка описания проблемы и СКРИНШОТА (в бинарном виде)"""
        description = message.text if message.content_type == 'text' else message.caption
        if not description:
            description = "Описание не указано"

        screenshot_data = None

        # Обработка фото
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            screenshot_data = bot.download_file(file_info.file_path)

        # Обработка документа (если это изображение)
        elif message.document:
            if message.document.mime_type and message.document.mime_type.startswith('image/'):
                if message.document.file_size > 10 * 1024 * 1024:
                    bot.send_message(message.chat.id, "⚠️ Файл слишком большой (макс. 10 МБ)")
                    return
                file_info = bot.get_file(message.document.file_id)
                screenshot_data = bot.download_file(file_info.file_path)

        # Сохраняем заявку
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            subcat = session.get(Subcategory, subcat_id)
            
            if user and subcat:
                ticket = Ticket(
                    user_id=user.id,
                    subcategory_id=subcat.id,
                    description=description,
                    status='В работе',          # ← сразу "В работе"
                    taken_at=datetime.now(),    # ← фиксируем время взятия
                    screenshot=screenshot_data, # ← бинарные данные
                    helped=False
                )
                session.add(ticket)
                session.commit()

                # Получаем клавиатуру пользователя
                user_keyboard = get_user_keyboard(
                    is_admin=user.is_admin,
                    is_it_specialist=user.is_it_specialist
                )

                bot.send_message(
                    message.chat.id,
                    f"✅ Заявка #{ticket.id} создана!\n"
                    f"Категория: {subcat.category.name} → {subcat.name}\n"
                    f"Статус: В работе\n"
                    f"Описание: {description}\n\n"
                    "Вы можете проверить статус заявки с помощью кнопки '📋 Мои заявки'.",
                    reply_markup=user_keyboard
                )

                # Уведомление IT-специалистам
                notify_it_specialists(ticket)
            else:
                # Даже при ошибке — показываем клавиатуру
                user_keyboard = get_user_keyboard()
                bot.send_message(
                    message.chat.id,
                    "⚠️ Ошибка создания заявки.",
                    reply_markup=user_keyboard
                )
                
                
    def notify_it_specialists(ticket):
        """Уведомляет IT-специалистов о новой заявке"""
        with Session() as session:
            it_specialists = session.query(User).filter_by(is_it_specialist=True).all()
            if not it_specialists:
                print("Нет IT-специалистов для уведомления")
                return

            short_desc = (ticket.description[:50] + '...') if len(ticket.description) > 50 else ticket.description
            message_text = (
                f"🆕 <b>Новая заявка</b> #{ticket.id}\n"
                f"Категория: {ticket.subcategory.category.name} → {ticket.subcategory.name}\n"
                f"Описание: {html.escape(short_desc)}\n"
                f"Время: {ticket.created_at.strftime('%d.%m %H:%M')}"
            )

            for specialist in it_specialists:
                try:
                    bot.send_message(specialist.telegram_id, message_text)
                except Exception as e:
                    print(f"Не удалось отправить уведомление {specialist.telegram_id}: {e}")                
    
                                
    @bot.message_handler(func=lambda msg: msg.text == "📋 Мои заявки")
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
            
            response = "📋 Ваши последние 10 заявок:\n\n"
            for ticket in tickets:
                # Цветовые индикаторы для актуальных статусов
                if ticket.status == "Закрыта":
                    status_color = "🟢"
                elif ticket.status == "В работе":
                    status_color = "🟠"
                elif ticket.status == "Ожидает уточнений":
                    status_color = "🔵"
                

                response += (
                    f"🔹 #{ticket.id}\n"
                    f"Категория: {ticket.subcategory.category.name} → {ticket.subcategory.name}\n"
                    f"Статус: {status_color} {ticket.status}\n"
                    f"Дата: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                )
                if ticket.closed_at:
                    response += f"Закрыта: {ticket.closed_at.strftime('%d.%m.%Y %H:%M')}\n"
                response += "\n"
            
            bot.send_message(message.chat.id, response)