import json
import os
from datetime import datetime 
from sqlalchemy import (BigInteger, Boolean, DateTime, Text, create_engine, exists,
                        Column, Integer, String, ForeignKey, LargeBinary)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import *

Base = declarative_base()

class User(Base):
    '''Таблица пользователей'''
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_it_specialist = Column(Boolean, default=False)
    
    tickets = relationship("Ticket", back_populates="user", cascade="all, delete")

class Category(Base):
    '''Основные категории проблем'''
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    
    subcategories = relationship("Subcategory", back_populates="category", cascade="all, delete")

class Subcategory(Base):
    '''Подкатегории с рекомендациями'''
    __tablename__ = 'subcategories'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String(100), nullable=False)
    recommendation = Column(Text, nullable=False)
    
    category = relationship("Category", back_populates="subcategories")
    tickets = relationship("Ticket", back_populates="subcategory")

class Ticket(Base):
    '''Таблица заявок'''
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    # связь с пользователем, создавшим заявку
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'), nullable=False)
    # свзяь с подкатегориями 
    description = Column(Text)
    # текстовое описание проблемы
    status = Column(String(20), default='Открыта', nullable=False)
    # статус заявки
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    # время создание заявки 
    taken_at = Column(DateTime, default=datetime.now)
    # время взятие в работу
    closed_at = Column(DateTime)
    # время закрытие заяки
    screenshot = Column(LargeBinary)
    # скрины или файлы храним в бинарном виде
    helped = Column(Boolean)
    # помогли ли рекомендации
    assigned_to = Column(BigInteger, nullable=True)  
    # telegram_id IT-специалиста
    
    user = relationship("User", back_populates="tickets")
    subcategory = relationship("Subcategory", back_populates="tickets")

# Инициализация базы данных
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
