# Security project (File Manager)
## Описание

Проект по компьютерной безопасности в виде веб-приложения для загрузки, хранения и обмена файлами с возможностью регистрации новых пользователей.

## Технологии
- FastAPI
- Docker
- Cryptography
- Pydantic
- Jinja2
- Bleach
- Bandit

## Инструкция по запуску

1. Клонировать репозиторий себе

```bash
git clone ...
```

2. Создать .env из примера

```bash
cp .env.example .env
```

3. Заполнить .env кодом из следующей команды

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

4. Запустить приложение

```bash
docker-compose up -d --build
```

5. Открыть Swagger UI

## Описание API

Интерактивная документация:
http://localhost:8000/docs

## Отчеты домашних заданий

Все отчеты домашних заданий с прилагающими скриншотами и файлами находится в папке /hw_reports