#!/bin/bash

# Устанавливаем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаем папку для данных
mkdir -p /opt/render/project/data