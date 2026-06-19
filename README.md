# DiceScream CRM

Веб-CRM на Django: **проекты**, **задачи (Kanban)**, **календарь**, **финансы**.  
Русский интерфейс, PWA (установка на телефон), авторизация через логин/пароль и Яндекс OAuth.

## Возможности

- **Роли:** администратор, редактор, наблюдатель
- **Модерация:** новые пользователи (регистрация / Яндекс) попадают в ожидание до назначения роли
- **Администратор:** полный доступ, редактирование любых записей, управление пользователями
- **PWA:** можно добавить на главный экран телефона

## Быстрый старт (локально)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux

pip install -r requirements.txt
copy .env.example .env         # или cp на Linux

python manage.py migrate
python manage.py setup_master
python manage.py seed_categories
python manage.py runserver
```

Откройте http://127.0.0.1:8000

**Мастер-аккаунт** (из `.env`):
- Логин: `EnotGod`
- Пароль: задаётся в `MASTER_PASSWORD`

## Яндекс OAuth

1. Создайте приложение на https://oauth.yandex.ru/
2. Redirect URI: `https://ваш-домен.ru/accounts/yandex/callback/`
3. Добавьте в `.env`:
   ```
   YANDEX_CLIENT_ID=ваш_id
   YANDEX_CLIENT_SECRET=ваш_секрет
   ```

## Деплой на VPS (Ubuntu 24.04, 2 ГБ RAM)

### 1. Подготовка сервера

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip nginx postgresql postgresql-contrib
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2. PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER crm_user WITH PASSWORD 'надёжный_пароль';"
sudo -u postgres psql -c "CREATE DATABASE crm_dicescream OWNER crm_user;"
```

### 3. Приложение

```bash
sudo mkdir -p /var/www/crm && sudo chown $USER:$USER /var/www/crm
cd /var/www/crm
git clone <ваш-репозиторий> .
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Отредактируйте .env:
# DEBUG=False
# USE_SQLITE=False
# ALLOWED_HOSTS=ваш-домен.ru
# CSRF_TRUSTED_ORIGINS=https://ваш-домен.ru
# SECRET_KEY=случайная_длинная_строка
# DB_* параметры PostgreSQL
# MASTER_PASSWORD=надёжный_пароль

python manage.py migrate
python manage.py setup_master
python manage.py seed_categories
python manage.py collectstatic --noinput
```

### 4. Gunicorn (systemd)

Файл `/etc/systemd/system/crm.service`:

```ini
[Unit]
Description=DiceScream CRM
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/crm
Environment="PATH=/var/www/crm/venv/bin"
ExecStart=/var/www/crm/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo chown -R www-data:www-data /var/www/crm
sudo systemctl enable crm && sudo systemctl start crm
```

### 5. Nginx + SSL

```nginx
server {
    listen 80;
    server_name ваш-домен.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ваш-домен.ru;

    ssl_certificate /etc/letsencrypt/live/ваш-домен.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ваш-домен.ru/privkey.pem;

    client_max_body_size 10M;

    location /static/ { alias /var/www/crm/staticfiles/; }
    location /media/  { alias /var/www/crm/media/; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo certbot --nginx -d ваш-домен.ru
```

### 6. Бэкапы БД (cron)

```bash
0 3 * * * pg_dump -U crm_user crm_dicescream | gzip > /var/backups/crm_$(date +\%Y\%m\%d).sql.gz
```

## Структура модулей

| Модуль    | URL           | Описание                          |
|-----------|---------------|-----------------------------------|
| Дашборд   | `/`           | Сводка по всем модулям            |
| Проекты   | `/projects/`  | CRUD проектов, участники, бюджет  |
| Задачи    | `/tasks/`     | Список и Kanban-доска             |
| Календарь | `/calendar/`  | События + дедлайны задач          |
| Финансы   | `/finance/`   | Доходы/расходы, категории, отчёты |
| Пользователи | `/accounts/users/` | Только для администратора   |

## Права доступа

| Действие              | Администратор | Редактор | Наблюдатель |
|-----------------------|:-------------:|:--------:|:-----------:|
| Просмотр              | ✅            | ✅       | ✅          |
| Создание/редактирование | ✅          | ✅       | ❌          |
| Удаление              | ✅            | своё*    | ❌          |
| Управление пользователями | ✅        | ❌       | ❌          |

\* Редактор может удалять только свои записи; администратор — любые.

## Безопасность

- Смените `SECRET_KEY` и `MASTER_PASSWORD` на продакшене
- Не коммитьте файл `.env` в git
- Используйте HTTPS и надёжные пароли PostgreSQL
