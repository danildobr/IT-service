from models import *

def create_tables(engine):
    Base.metadata.drop_all(engine) # удаление таблиц
    Base.metadata.create_all(engine) # создание всех таблиц


def add_category(session, json_file='data_category.json'):
    """Загружает категории и подкатегории из JSON файла"""
    try:
        #  Получаем абсолютный путь к файлу
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, json_file)
        
        print(f"Пытаемся загрузить файл: {json_path}")  # Отладочная информация
        
        if not os.path.exists(json_path):
            print(f"❌ Файл не найден: {json_path}")
            print("Содержимое директории:")
            print(os.listdir(current_dir))  # Покажем что есть в папке
            return
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        added_categories = 0
        added_subcategories = 0
        
        for category_data in data['categories']:
            # Проверяем существование основной категории
            category = session.query(Category).filter_by(name=category_data['name']).first()
            
            if not category:
                category = Category(name=category_data['name'])
                session.add(category)
                session.flush()  # Получаем ID для новой категории
                added_categories += 1
            
            # Добавляем подкатегории
            for subcat_data in category_data['subcategories']:
                subcategory = session.query(Subcategory).filter_by(
                    category_id=category.id,
                    name=subcat_data['name']
                ).first()
                
                if not subcategory:
                    subcategory = Subcategory(
                        category_id=category.id,
                        name=subcat_data['name'],
                        recommendation=subcat_data['recommendation']
                    )
                    session.add(subcategory)
                    added_subcategories += 1
        
        session.commit()
        print(f"Добавлено: {added_categories} категорий, {added_subcategories} подкатегорий")
        
    except Exception as e:
        session.rollback()
        print(f"Ошибка при загрузке категорий: {e}")        
        



def check_user(session, message):
    '''Проверяем пользователя'''
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        return user
    except Exception as e:
        print(f'Ошибка в проверке пользователя: {e}')
              

def get_or_create_user(session, message):
    '''Получаем или создаем пользователя'''
    try:
        user = check_user(session, message)
        
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )
            session.add(user)
            session.commit()
            print(f'Пользователь добавлен: {message.from_user.username}')
            return user
        
        return user
    except Exception as e:
        print(f'Ошибка в получение или создаем пользователя: {e}')
        
        
        
        
        