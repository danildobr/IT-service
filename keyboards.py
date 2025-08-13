from telebot import types

def keyboard_category(categories):
    '''Создаём клавиатуру для категорий'''
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    buttons = [types.KeyboardButton(cat.name) for cat in categories]
    keyboard.add(*buttons)  # распаковываем список кнопок
    keyboard.add(types.KeyboardButton("Отмена"))

    return keyboard