# HH AutoApply Bot

Telegram-бот + Mini App для автоматических откликов на вакансии hh.ru.
Личное использование. Полная спецификация — `Спецификация.md` в исходной папке проекта.

## Быстрый старт (локально, Windows + Docker Desktop)

1. Убедитесь, что Docker Desktop запущен (иконка кита в трее).
2. В корне репозитория должен быть файл `.env` (создаётся вручную, не в git).
   Шаблон: `.env.example`. Минимум: `BOT_TOKEN`, `ADMIN_TG_ID`, `OPENROUTER_API_KEY`, `COOKIES_ENC_KEY`.
3. Запуск:
   ```powershell
   docker compose up -d --build
   docker compose logs -f bot
   ```
4. В Telegram открыть своего бота → нажать **/start**. Должен ответить.

## Команды Docker (шпаргалка)

| Что нужно                                | Команда                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| Запустить всё                            | `docker compose up -d`                                             |
| Пересобрать после изменений зависимостей | `docker compose up -d --build`                                     |
| Логи бота                                | `docker compose logs -f bot`                                       |
| Перезапустить бота                       | `docker compose restart bot`                                       |
| Остановить всё                           | `docker compose down`                                              |
| Снести с базой (полный сброс)            | `docker compose down -v`                                           |
| Применить миграции                       | `docker compose exec bot alembic upgrade head`                     |
| Создать миграцию                         | `docker compose exec bot alembic revision --autogenerate -m "msg"` |

## Структура

См. §11 спецификации. На этапе 1 реализованы: skeleton, БД, Redis, whitelist, rate-limit,
команды `/start /help /menu /whitelist /feedback /cancel`.

## Этапы

См. §10 спецификации (17 этапов).
