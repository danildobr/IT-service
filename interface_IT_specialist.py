from models import *
from interface_user import bot

# Добавляем в начало файла
IT_SPECIALIST_COMMANDS = ['take', 'close', 'mytickets', 'request_info']



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
    # Взять заявку в работу
    elif message.text.startswith('/close'):
        close_ticket(message)
    # Закрыть заявку
    elif message.text.startswith('/mytickets'):
        show_my_tickets(message)
    # Показать заявки в работе у специалиста
    elif message.text.startswith('/request_info'):
        request_additional_info(message)
    # Запросить дополнительную информацию

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