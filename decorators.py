from telebot import TeleBot
from models import Session, User
from bot import bot


def user_required(func):
    def wrapper(message):
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if not user:
                bot.reply_to(message, "⛔ Пожалуйста, начните с /start")
                return
        return func(message)
    return wrapper

def it_specialist_required(func):
    def wrapper(message):
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if not user or not user.is_it_specialist:
                bot.reply_to(message, "⛔ Требуются права ИТ-специалиста")
                return
        return func(message)
    return wrapper

def admin_required(func):
    def wrapper(message):
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if not user or not user.is_admin:
                bot.reply_to(message, "⛔ Требуются права администратора")
                return
        return func(message)
    return wrapper