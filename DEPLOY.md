# Инструкция по деплою AtelierAI на VPS (Linux / Ubuntu)

В данном руководстве описан процесс развертывания проекта на чистом Linux-сервере (Ubuntu 20.04/22.04+) с использованием **Nginx** (для раздачи статики фронтенда и проксирования запросов) и **systemd** (для надежного автозапуска бэкенда FastAPI).

---

## 1. Системные требования и зависимости
Подключитесь к VPS по SSH и обновите пакеты:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git nginx -y
```

---

## 2. Клонирование проекта
Склонируйте репозиторий в рабочую директорию (например, `/var/www/`):
```bash
cd /var/www
git clone git@github.com:spelingbee/atelier-ai.git
cd atelier-ai
```

---

## 3. Настройка Бэкенда (FastAPI)

1. **Создание виртуального окружения Python:**
   ```bash
   cd /var/www/atelier-ai/ateiler_back
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Установка зависимостей:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.backend.txt
   ```

3. **Создание файла конфигурации `.env`:**
   Создайте файл `/var/www/atelier-ai/ateiler_back/.env` и пропишите туда ваши ключи и настройки:
   ```env
   # Выбор ИИ-провайдера (gemini, anthropic или mock для оффлайна)
   AI_PROVIDER=gemini
   
   # Ключи API (укажите ваш рабочий ключ)
   GOOGLE_API_KEY=AIzaSy...
   
   # Локальный бэкенд хранения данных
   STORAGE_BACKEND=local
   ```

4. **Автозапуск через Systemd (Демонизация):**
   Создайте файл системной службы `/etc/systemd/system/atelier-backend.service`:
   ```bash
   sudo nano /etc/systemd/system/atelier-backend.service
   ```
   Вставьте следующее содержимое:
   ```ini
   [Unit]
   Description=AtelierAI FastAPI Backend
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/var/www/atelier-ai/ateiler_back
   Environment="PATH=/var/www/atelier-ai/ateiler_back/venv/bin"
   ExecStart=/var/www/atelier-ai/ateiler_back/venv/bin/uvicorn app_ext:app --host 127.0.0.1 --port 8000 --workers 2
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Запустите и добавьте сервис в автозагрузку:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start atelier-backend
   sudo systemctl enable atelier-backend
   ```
   *Проверить статус работы бэкенда можно командой:* `sudo systemctl status atelier-backend`

---

## 4. Настройка Фронтенда и Nginx

Мы настроим Nginx так, чтобы он раздавал файлы фронтенда статически на порту `80`, а запросы к `/api/v1` и `/api/v2` автоматически перенаправлял на запущенный FastAPI бэкенд на порту `8000`.

1. **Создайте файл конфигурации хоста Nginx:**
   ```bash
   sudo nano /etc/nginx/sites-available/atelier-ai
   ```
   Вставьте конфигурацию:
   ```nginx
   server {
       listen 80;
       server_name atelier.kataloga.org;

       # Фронтенд (раздача статики)
       location / {
           root /var/www/atelier-ai/ateiker_front;
           index index.html;
           try_files $uri $uri/ /index.html;
       }

       # Проксирование запросов к бэкенду
       location /api/ {
           proxy_pass http://127.0.0.1:8000/api/;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }

       # Раздача сохраненных локально PDF/SVG выкроек
       location /files/ {
           proxy_pass http://127.0.0.1:8000/files/;
           proxy_set_header Host $host;
       }
   }
   ```

2. **Активируйте конфигурацию и перезапустите Nginx:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/atelier-ai /etc/nginx/sites-enabled/
   sudo rm /etc/nginx/sites-enabled/default  # Удалить дефолтный конфиг Nginx, если есть
   sudo nginx -t                             # Проверить корректность синтаксиса
   sudo systemctl restart nginx
   ```

3. **Права доступа к файлам для сохранения выкроек:**
   Чтобы бэкенд мог сохранять файлы в папку `/data/skirt/storage/`, нужно дать права пользователю `www-data` (под которым работает сервис бэкенда):
   ```bash
   sudo mkdir -p /data/skirt/storage
   sudo chown -R www-data:www-data /data/skirt
   sudo chmod -R 775 /data/skirt
   ```

---

## 5. Обновление проекта (CI/CD вручную)
Для деплоя обновлений достаточно зайти на VPS и выполнить:
```bash
cd /var/www/atelier-ai
git pull
sudo systemctl restart atelier-backend
```

---

## 6. (Опционально) Настройка HTTPS через Let's Encrypt
Для получения бесплатного SSL-сертификата установите Certbot:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d atelier.kataloga.org
```
Certbot сам автоматически изменит конфигурацию Nginx под HTTPS и настроит автопродление сертификата.
