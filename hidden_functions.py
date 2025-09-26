from models import *

def hidden_functions(bot):
    """Обработчики для административных команд"""
    
    @bot.message_handler(commands=['add_it'])
    def handle_make_me_it_specialist(message):
        """Добавляет текущего пользователя в IT-специалисты"""
        try:
            with Session() as session:
                user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
                if not user:
                    bot.send_message(message.chat.id, "❌ Пользователь не найден")
                    return
                
                user.is_admin = False
                user.is_it_specialist = True
                session.commit()
                
                bot.send_message(
                    message.chat.id, 
                    f"✅ Вы теперь IT-специалист! @{user.username}\n"
                    "Перезапустите бота командой /start для обновления меню."
                )
                    
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    @bot.message_handler(commands=['add_admin'])
    def handle_make_me_admin(message):
        """Добавляет текущего пользователя в администраторы"""
        try:
            with Session() as session:
                user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
                if not user:
                    bot.send_message(message.chat.id, "❌ Пользователь не найден")
                    return
                
                user.is_admin = True
                user.is_it_specialist = False  # Удаляем из IT-специалистов
                session.commit()
                
                bot.send_message(
                    message.chat.id, 
                    f"✅ Вы теперь администратор! @{user.username}\n"
                    "Перезапустите бота командой /start для обновления меню."
                )
                    
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    @bot.message_handler(commands=['add_user'])
    def handle_remove_my_roles(message):
        """Удаляет специальные роли у текущего пользователя"""
        try:
            with Session() as session:
                user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
                if not user:
                    bot.send_message(message.chat.id, "❌ Пользователь не найден")
                    return
                
                user.is_admin = False
                user.is_it_specialist = False
                session.commit()
                
                bot.send_message(
                    message.chat.id, 
                    f"✅ С вас сняты специальные роли! @{user.username}\n"
                    "Перезапустите бота командой /start для обновления меню."
                )
                    
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")