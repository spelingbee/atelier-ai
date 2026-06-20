# AtelierAI — Backend (новые файлы)

Эти файлы ДОБАВЛЯЮТСЯ рядом с `patterns.py` и `export.py`. Исходные файлы не меняются.

## Слои (снизу вверх)

```
patterns.py  export.py        ← движок (без изменений)
      ↑
service.py                    ← оркестрация, НЕ зависит от фреймворка
  ↗      ↖
ai_classifier.py  db.py  storage.py
      ↑
api.py                        ← тонкая FastAPI-обёртка
```

## Файлы

| Файл | Назначение |
|---|---|
| `ai_classifier.py` | LLM-классификатор (Claude tool use). Без `ANTHROPIC_API_KEY` — оффлайн mock |
| `storage.py` | LocalStorage (MVP) / S3Storage (production), единый интерфейс |
| `db.py` | sqlite3 из stdlib (MVP). Для Postgres — `schema.postgres.sql` + asyncpg |
| `service.py` | analyze() / generate() / export_links() — ядро, тестируемо без сети |
| `api.py` | FastAPI: /sessions /analyze /generate /export /health |
| `test_service.py` | сквозной тест без FastAPI |

## Запуск

```bash
pip install -r requirements.backend.txt
export ANTHROPIC_API_KEY=sk-...        # опционально; без ключа — mock-классификатор
uvicorn api:app --reload --port 8000
```

## Сквозной флоу

```bash
# 1. создать сессию
curl -X POST localhost:8000/api/v1/sessions
# 2. загрузить фото -> тип юбки
curl -X POST localhost:8000/api/v1/analyze -F session_id=<sid> -F file=@skirt.jpg
# 3. мерки -> лекало
curl -X POST localhost:8000/api/v1/generate -H 'Content-Type: application/json' \
     -d '{"session_id":"<sid>","waist_cm":70,"hip_cm":98,"length_cm":70}'
# 4. скачать
curl localhost:8000/api/v1/export/<job_id>?format=pdf
```

## Переход на production

- `STORAGE_BACKEND=s3` + S3_* переменные → файлы в S3/MinIO.
- Postgres: примени `schema.postgres.sql`, перепиши `db.py` на asyncpg (сигнатуры функций те же).
- `ANTHROPIC_API_KEY` → реальный классификатор.
