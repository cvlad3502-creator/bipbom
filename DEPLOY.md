# Деплой BipBom на Render.com (бесплатно)

## Что уже готово

- `app.py` — точка входа для Render: держит открытый порт (Render требует) и запускает бота.
- `render.yaml` — конфиг сервиса.
- `requirements.txt`, `runtime.txt`, `Procfile` — сборка.
- `render-upload.zip` — архив с кодом (без базы, токена и логов).

## Шаг 1. Аккаунт

1. Откройте https://render.com и нажмите **Sign up**.
2. Войдите через GitHub или по email. Карта не нужна.

## Шаг 2. Загрузить код

1. В дашборде: **New +** → **Web Service**.
2. Внизу выберите **Deploy an existing image**? Нет — нужна ветка **Public Git repository** или **Upload**:
   - Render не умеет «залить ZIP» как Heroku. Проще всего:
   - **Вариант A (без GitHub):** New + → **Blueprint** → репозиторий обязательно.
   - **Вариант B (самый простой):** зарегистрируйтесь на https://github.com, создайте пустой репозиторий `bipbom`, нажмите «uploading an existing file» и перетащите файлы из папки `BipBom` **кроме** `bipbom.db`, `token.txt`, `log.txt`, `.venv`. Commit.
   - В Render: New + → **Web Service** → **Build and deploy from a Git repository** → подключите GitHub → выберите `bipbom`.

## Шаг 3. Настройки сервиса

| Поле | Значение |
|---|---|
| Name | `bipbom` |
| Region | Frankfurt (EU Central) |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |
| Instance Type | **Free** |
| Health Check Path | `/` |

## Шаг 4. Секреты (Environment)

Во вкладке **Environment** добавьте:

| Key | Value |
|---|---|
| `BOT_TOKEN` | токен от @BotFather |
| `ADMIN_ID` | ваш Telegram ID (число) |
| `WEBAPP_URL` | пока пусто, заполните позже |

Нажмите **Save** → сервис пересоберётся.

## Шаг 5. Проверка

1. В логах Render должно быть: `BipBom запущен. WEBAPP_URL: не задан`.
2. В Telegram: `/start`.

Если в логах `Cannot connect to host api.telegram.org` — Render в выбранном регионе не пропускает Telegram. Смените Region на **Oregon (US West)** или **Ohio (US East)** и пересоберите.

## Шаг 6. Чтобы бот не засыпал

Бесплатный сервис Render спит через 15 минут без запросов. Варианты:

- **UptimeRobot** (бесплатно): создайте HTTP-монитор на ваш адрес `https://bipbom.onrender.com/` с интервалом 5 минут. Бот будет бодрствовать.
- Без монитора: после паузы первый ответ в Telegram придёт через ~1 минуту.

## Шаг 7. WebApp (страница)

Сейчас страница — локальный `web/index.html`, в облаке её отдаёт бот только через кнопку `WEBAPP_URL`. Чтобы открыть в Telegram:

1. В Render откройте ваш сервис → URL вида `https://bipbom.onrender.com`.
2. Адрес страницы — `https://bipbom.onrender.com/` не отдаёт HTML (это health-заглушка). Поэтому WebApp из облака пока не работает — нужен отдельный статический хостинг.
3. Бесплатный вариант: **Render → New + → Static Site** из того же репозитория, папка `web`. Получите `https://bipbom-web.onrender.com/` и вставьте в `WEBAPP_URL`.

## Важно

- База `bipbom.db` на Render живёт в памяти сервиса и сбрасывается при пересборке. Для теста это нормально; для сохранения балансов нужна платная дисковая привязка ($7/мес).
- Не заливайте `token.txt`, `bipbom.db` в GitHub: токен утечёт.
