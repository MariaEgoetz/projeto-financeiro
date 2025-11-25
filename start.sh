#!/bin/bash

# Sai do script se der erro em qualquer comando
set -e

echo "Rodando Migrations..."
python manage.py migrate

echo "Iniciando Celery Worker em Background..."
# O '&' no final faz ele rodar em segundo plano
# Usamos --concurrency=1 para gastar pouca memória do servidor grátis
celery -A core worker --loglevel=info --concurrency=1 &

echo "Iniciando Gunicorn (Servidor Web)..."
# O Render injeta a variável PORT automaticamente
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT