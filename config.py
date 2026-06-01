import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    database_url = os.environ.get('DATABASE_URL')

    # Если используем Supabase (postgres), добавляем sslmode
    if database_url and 'postgres' in database_url:
        if 'sslmode' not in database_url:
            database_url += '?sslmode=require'

    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False