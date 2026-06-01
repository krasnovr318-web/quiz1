import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'K7m9pX2vL5nB8qR4wE1yU6iO3sA0dG9h')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False