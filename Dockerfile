FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema (necessário para numpy e outros)
RUN apt-get update && apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código para dentro do container
COPY . /app/

# Dá permissão de execução para o script de inicialização
RUN chmod +x /app/start.sh

EXPOSE 8000

# O comando final será substituído pelo render.yaml, mas deixamos um padrão aqui
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]