import json
import os
from datetime import datetime 
from sqlalchemy import (Boolean, DateTime, Text, create_engine, exists,
                        Column, Integer, String, ForeignKey)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import *

Base = declarative_base()

class User(Base):
    '''Таблица пользователей'''
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False)           # флаги прав доступа
    is_it_specialist = Column(Boolean, default=False)   # флаги прав доступа
    
    tickets = relationship("Ticket", back_populates="user", cascade="all, delete")

class Category(Base):
    '''Таблица категорий проблем'''
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    advice = Column(Text, nullable=False)
    
    tickets = relationship("Ticket", back_populates="category")

class Ticket(Base):
    '''Таблица заявок'''
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    # связь с пользователем, создавшим заявку
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    # категория проблемы
    description = Column(Text)
    # текстовое описание проблемы
    status = Column(String(20), default='Открыт', nullable=False)
    # статусы: "Открыт", "В работе", "Закрыт"
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    # создание заявки 
    taken_at = Column(DateTime)
    # взятие в работу
    closed_at = Column(DateTime)
    # закрытие заяки
    file_path = Column(String(255))
    # путь к прикреплённому файлу (скриншоты, PDF и др.)
    helped = Column(Boolean)
    # помогли ли рекомендации
    
    user = relationship("User", back_populates="tickets")
    category = relationship("Category", back_populates="tickets")

# Инициализация базы данных
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def create_tables(engine):
    Base.metadata.drop_all(engine) # удаление таблиц
    Base.metadata.create_all(engine) # создание всех таблиц


def add_category(session, json_file='data_category.json'):
    """Загружает категории из JSON-файла и добавляет в БД,
        если их ещё нет."""
    # Проверяем, существует ли файл
    if not os.path.exists(json_file):
        print(f"❌ Файл не найден: {json_file}")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)

        added_count = 0
        for item in categories_data:
            name = item["category"].strip()
            advice = item["advice"].strip()

            # Проверяем, существует ли категория в БД
            existing = session.query(Category).filter_by(name=name).first()
            if existing:
                print(f"🔸 Категория существует: {name}")
                continue

            # Добавляем новую
            new_category = Category(name=name, advice=advice)
            session.add(new_category)
            print(f"✅ Добавлена: {name} → {advice}")
            added_count += 1

        session.commit()
        print(f"\n✅ Успешно добавлено новых категорий: {added_count}")

    except Exception as e:
        print(f"❌ Ошибка при добавлении категорий: {e}")
        session.rollback()



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
        
        
        
        
        