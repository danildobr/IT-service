from telebot import types
from models import *
from models import *
from datetime import datetime
from telebot import types

# Команды администратора
ADMIN_COMMANDS = ['users', 'statistics', 'add_it', 'remove_it', 'broadcast', 'delete_ticket']

def register_admin_handlers(bot):
    
    @bot.message_handler(commands=ADMIN_COMMANDS)
    def check_admin(message):
        """Проверка прав администратора"""
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if not user or not user.is_admin:
                bot.reply_to(message, "⛔ Команда только для администраторов")
                return
        
        # Перенаправление на обработчики
        if message.text.startswith('/users'):
            list_users(message)
        elif message.text.startswith('/statistics'):
            show_stats(message)
        elif message.text.startswith('/add_it'):
            add_it_specialist(message)
        elif message.text.startswith('/remove_it'):
            remove_it_specialist(message)
        elif message.text.startswith('/broadcast'):
            start_broadcast(message)
        elif message.text.startswith('/delete_ticket'):
            handle_delete_ticket(message)
            

    def list_users(message):
        """Список всех пользователей"""
        with Session() as session:
            users = session.query(User).order_by(User.id.desc()).limit(100).all()
            
            if not users:
                bot.reply_to(message, "📭 Нет пользователей в системе")
                return

            message_parts = []
            current_part = "👥 <b>Список пользователей</b>:\n\n"
            
            for user in users:
                user_info = (
                    f"ID: {user.id} | @{user.username}\n"
                    f"Телеграм ID: {user.telegram_id}\n"
                    f"Роли: {'Админ' if user.is_admin else ''} "
                    f"{'ИТ-спец' if user.is_it_specialist else 'Пользователь'}\n"
                    f"────────────────────\n"
                )
                
                if len(current_part) + len(user_info) > 4000:
                    message_parts.append(current_part)
                    current_part = user_info
                else:
                    current_part += user_info

            if current_part:
                message_parts.append(current_part)

            for part in message_parts:
                bot.send_message(message.chat.id, part, parse_mode='HTML')

    def show_stats(message):
        """Статистика системы"""
        with Session() as session:
            stats = {
                'users': session.query(User).count(),
                'tickets': session.query(Ticket).count(),
                'open_tickets': session.query(Ticket).filter_by(status='Открыт').count(),
                'in_work': session.query(Ticket).filter_by(status='В работе').count(),
            }
            
            text = (
                "📊 <b>Статистика системы</b>\n\n"
                f"👤 Пользователей: {stats['users']}\n"
                f"📝 Всего заявок: {stats['tickets']}\n"
                f"🟡 Открытых: {stats['open_tickets']}\n"
                f"🟠 В работе: {stats['in_work']}\n"
                f"🟢 Закрытых: {stats['tickets'] - stats['open_tickets'] - stats['in_work']}"
            )
            bot.send_message(message.chat.id, text, parse_mode='HTML')

    def add_it_specialist(message):
        """Добавить ИТ-специалиста"""
        try:
            user_id = message.text.split()[1]
            with Session() as session:
                user = session.query(User).filter(
                    (User.telegram_id == user_id) | 
                    (User.username == user_id.strip('@'))
                ).first()
                
                if user:
                    user.is_it_specialist = True
                    session.commit()
                    bot.reply_to(message, f"✅ @{user.username} назначен ИТ-специалистом")
                else:
                    bot.reply_to(message, "❌ Пользователь не найден")
        except Exception as e:
             bot.reply_to(message,f"❌ Ошибка: {str(e)}, для добавления формат /remove_it <телеграм ID или имя>")

    def remove_it_specialist(message):
        """Удалить ИТ-специалиста"""
        try:
            user_id = message.text.split()[1]
            with Session() as session:
                user = session.query(User).filter(
                    (User.telegram_id == user_id) | 
                    (User.username == user_id.strip('@'))
                ).first()
                
                if user:
                    user.is_it_specialist = False
                    session.commit()
                    bot.reply_to(message, f"✅ @{user.username} больше не ИТ-специалист")
                else:
                    bot.reply_to(message, "❌ Пользователь не найден")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка: {str(e)}, формат для удаления /remove_it <телеграм ID или имя>")

    def start_broadcast(message):
        """Начать рассылку"""
        msg = bot.reply_to(message, "📢 Введите сообщение для рассылки:")
        bot.register_next_step_handler(msg, process_broadcast)

    def process_broadcast(message):
        """Обработать рассылку"""
        with Session() as session:
            users = session.query(User).all()
            success = 0
            for user in users:
                try:
                    bot.send_message(user.telegram_id, f"📢 <b>Рассылка</b>:\n\n{message.text}", parse_mode='HTML')
                    success += 1
                except:
                    continue
            
            bot.reply_to(message, f"✅ Рассылка завершена\nОтправлено: {success}/{len(users)}")
    
    @bot.message_handler(commands=['delete_ticket'])
    def handle_delete_ticket(message):
        """Обработчик удаления заявки с подтверждением"""
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.reply_to(message, "❌ Формат: /delete_ticket <ID заявки>")
                return

            ticket_id = int(args[1])
            
            with Session() as session:

                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                
                if not ticket:
                    bot.reply_to(message, f"❌ Заявка #{ticket_id} не найдена")
                    return

                # Создаем клавиатуру подтверждения
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_del_{ticket_id}"),
                    types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_del")
                )
                
                bot.send_message(
                    message.chat.id,
                    f"⚠️ Вы уверены, что хотите полностью удалить заявку #{ticket_id}?\n"
                    f"Категория: {ticket.subcategory.category.name}\n"
                    f"Пользователь: @{ticket.user.username}\n"
                    f"Это действие нельзя отменить!",
                    reply_markup=markup
                )

        except ValueError:
            bot.reply_to(message, "❌ Некорректный ID заявки")
        except Exception as e:
            bot.reply_to(message, f"⚠️ Ошибка: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
    def confirm_delete(call):
        """Подтверждение удаления"""
        ticket_id = int(call.data.split('_')[-1])
        
        with Session() as session:
            try:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if ticket:
                    # Удаляем файлы, если они есть
                    if ticket.file_path and os.path.exists(ticket.file_path):
                        os.remove(ticket.file_path)
                    
                    session.delete(ticket)
                    session.commit()
                    
                    bot.edit_message_text(
                        f"✅ Заявка #{ticket_id} полностью удалена",
                        call.message.chat.id,
                        call.message.message_id
                    )
                else:
                    bot.answer_callback_query(call.id, "Заявка уже удалена")

            except Exception as e:
                session.rollback()
                bot.edit_message_text(
                    f"❌ Ошибка удаления: {str(e)}",
                    call.message.chat.id,
                    call.message.message_id
                )

    @bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
    def cancel_delete(call):
        """Отмена удаления"""
        bot.edit_message_text(
            "❌ Удаление отменено",
            call.message.chat.id,
            call.message.message_id
        )