from telebot import TeleBot
from config import TOKEN
from interface_user import register_user_handlers
from interface_IT_specialist import register_it_handlers
from interface_administrator import register_admin_handlers
from models import *
from working_db import *

bot = TeleBot(TOKEN)

# настройка БД: 1-создание таблиц
                # 2-заполенеие БД
                # 3-добавление ИТ специалистов в БД
# with Session() as session:
    #     create_tables(engine)
        # add_category(session)
# setup_it_specialists()
# setup_admins()
        

register_user_handlers(bot)
register_it_handlers(bot)
register_admin_handlers(bot) 

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)