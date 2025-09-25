from interface_user import register_user_handlers
from interface_IT_specialist import register_it_handlers
from interface_administrator import register_admin_handlers
from models import *
from working_db import *
from bot import bot
from hidden_functions import *

# with Session() as session:
#         create_tables(engine)
#         # создание таблиц
        # add_category(session)
#         # заполенеие БД
# setup_it_specialists()
# # добавление ИТ специалистов в БД
# setup_admins()
# # добавление админа в БД
        

register_user_handlers(bot)
register_it_handlers(bot)
register_admin_handlers(bot) 
hidden_functions(bot)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)