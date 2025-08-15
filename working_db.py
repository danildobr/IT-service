from models import *
import os 
from dotenv import load_dotenv

load_dotenv()


def create_tables(engine):
    Base.metadata.drop_all(engine) # удаление таблиц
    Base.metadata.create_all(engine) # создание всех таблиц


def add_category(session, json_file='data_category.json'):
    """Загружает категории и подкатегории из JSON файла с обновлением рекомендаций"""
    try:
        # Получаем абсолютный путь к файлу
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, json_file)
        
        print(f"Пытаемся загрузить файл: {json_path}")

        if not os.path.exists(json_path):
            print(f"❌ Файл не найден: {json_path}")
            print("Содержимое директории:")
            print(os.listdir(current_dir))
            return
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        added_categories = 0
        added_subcategories = 0
        updated_recommendations = 0

        for category_data in data['categories']:
            # Проверяем/создаем категорию
            category = session.query(Category).filter_by(name=category_data['name']).first()
            
            if not category:
                category = Category(name=category_data['name'])
                session.add(category)
                session.flush()
                added_categories += 1
                print(f"Добавлена новая категория: {category.name}")
            
            # Обрабатываем подкатегории
            for subcat_data in category_data['subcategories']:
                subcategory = session.query(Subcategory).filter_by(
                    category_id=category.id,
                    name=subcat_data['name']
                ).first()
                
                if not subcategory:
                    # Создаем новую подкатегорию
                    subcategory = Subcategory(
                        category_id=category.id,
                        name=subcat_data['name'],
                        recommendation=subcat_data['solution']
                    )
                    session.add(subcategory)
                    added_subcategories += 1
                    print(f"Добавлена подкатегория: {category.name} → {subcategory.name}")
                else:
                    # Проверяем, изменилась ли рекомендация
                    if subcategory.recommendation != subcat_data['solution']:
                        old_rec = subcategory.recommendation
                        subcategory.recommendation = subcat_data['solution']
                        updated_recommendations += 1
                        print(f"Обновлена рекомендация для: {subcategory.name}\n"
                              f"Было: {old_rec}\n"
                              f"Стало: {subcategory.recommendation}")
        
        session.commit()
        print(f"\nИтог:\n"
              f"Добавлено категорий: {added_categories}\n"
              f"Добавлено подкатегорий: {added_subcategories}\n"
              f"Обновлено рекомендаций: {updated_recommendations}")

    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка при загрузке категорий: {str(e)}")
        raise     
        

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
        

def setup_it_specialists():
    """Загружает IT-специалистов из .env в базу данных"""
    
    it_specialists_str = os.getenv('IT_SPECIALIST', '')
    if not it_specialists_str:
        print("⚠️ В .env не найдена переменная IT_SPECIALIST")
        return
    
    it_specialist_ids = [int(id_str.strip()) for id_str in it_specialists_str.split(',') if id_str.strip().isdigit()]
    
    if not it_specialist_ids:
        print("⚠️ Не найдено валидных ID в IT_SPECIALIST")
        return
    
    with Session() as session:
        added_count = 0
        updated_count = 0
        
        for telegram_id in it_specialist_ids:
            try:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if user:
                    if not user.is_it_specialist:
                        user.is_it_specialist = True
                        updated_count += 1
                else:
                    # Создаем пользователя с временным username
                    user = User(
                        telegram_id=telegram_id,
                        username=f"it_specialist_{telegram_id}",  # Временное значение
                        is_it_specialist=True,
                        is_admin=False
                    )
                    session.add(user)
                    added_count += 1
                
                session.commit()
                
            except Exception as e:
                session.rollback()
                print(f"⚠️ Ошибка обработки ID {telegram_id}: {e}")
        
        print(f"✅ Готово! Добавлено: {added_count}, Обновлено: {updated_count} IT-специалистов")
        

def setup_admins():
    """Загружает администраторов из .env в базу данных"""
    
    # Получаем список ID администраторов из .env
    admins_str = os.getenv('ADMIN_ID', '')
    if not admins_str:
        print("⚠️ В .env не найдена переменная ADMIN_ID")
        return
    
    # Парсим ID администраторов
    admin_ids = [int(id_str.strip()) for id_str in admins_str.split(',') if id_str.strip().isdigit()]
    
    if not admin_ids:
        print("⚠️ Не найдено валидных ID в ADMIN_ID")
        return
    
    with Session() as session:
        added_count = 0
        updated_count = 0
        
        for telegram_id in admin_ids:
            try:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if user:
                    if not user.is_admin:
                        user.is_admin = True
                        updated_count += 1
                        print(f"🛠 Пользователь {user.username} назначен администратором")
                else:
                    # Создаем нового пользователя-администратора
                    user = User(
                        telegram_id=telegram_id,
                        username=f"admin_{telegram_id}",  # Временное имя
                        is_admin=True,
                        is_it_specialist=True  # Админ автоматически получает права IT-спеца
                    )
                    session.add(user)
                    added_count += 1
                    print(f"👑 Создан новый администратор с ID {telegram_id}")
                
                session.commit()
                
            except Exception as e:
                session.rollback()
                print(f"⚠️ Ошибка обработки ID {telegram_id}: {e}")
        
        print(f"✅ Готово! Добавлено: {added_count}, Обновлено: {updated_count} администраторов")
