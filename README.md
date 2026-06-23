# vdbench_exporter
Создать экспортер данных VDbench в Prometheus, работающий в режиме онлайн, без задержек и определить, каких скоростей можно добиться. Экспортер должен собирать данные в валидный для Prometheus формат. Он должен поддерживать онлайн и офлайн режимы.

## Запуск

Установка зависимостей
```bash
pip install -r requirements.txt
```
Пример команды запуска
```bash
python -m src.main \
  --mode online \
  --vdbench-path "C:\vdbench\vdbench.bat" \
  --workload workload.txt
```
Мутрики будут отображаться на http://localhost:8000/metrics

# Внешнее управление остановкой экспортера

Экспортер поддерживает внешнее управление остановкой через HTTP API.

# Режим API

Запуск экспортера:

```bash
python -m src.main \
  --output-file output/flatfile.html \
  --stop-mode api \
  --api-port 8080
```

После запуска экспортер поднимает:

* endpoint с Prometheus-метриками
* API для управления процессом


# Доступные endpoint'ы

## Проверка состояния экспортера

```http
GET /health
```

Пример запроса:

```bash
curl http://localhost:8080/health
```

Пример ответа:

```json
{
  "status": "ok",
  "reader_running": true,
  "shutdown_requested": false,
  "output_file_exists": true,
  "last_metrics_update": 1716900000,
  "seconds_since_last_update": 2,
  "mode": "api",
  "uptime_seconds": 153
}
```

Описание полей:

| Поле                      | Описание                                      |
| ------------------------- | --------------------------------------------- |
| status                    | Состояние экспортера (`ok` / `degraded`)      |
| reader_running            | Активно ли чтение VDbench output              |
| shutdown_requested        | Был ли получен сигнал остановки               |
| output_file_exists        | Существует ли output-файл VDbench             |
| last_metrics_update       | Timestamp последнего обновления метрик        |
| seconds_since_last_update | Сколько секунд прошло с последнего обновления |
| mode                      | Текущий режим остановки                       |
| uptime_seconds            | Время работы экспортера                       |

---

## Остановка экспортера

```http
POST /shutdown
```

Пример запроса:

```bash
curl -X POST http://localhost:8080/shutdown
```

Пример ответа:

```json
{
  "status": "stopping"
}
```

После получения команды экспортер:

1. Останавливает чтение output-файла VDbench
2. Завершает фоновые задачи
3. Корректно завершает работу приложения

---

# Примеры интеграции

## PowerShell

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri http://localhost:8080/shutdown
```

---

## Python

```python
import requests

requests.post(
    "http://localhost:8080/shutdown"
)
```

---

## Bash

```bash
curl -X POST \
  http://localhost:8080/shutdown
```

---

# Типовой сценарий использования

## 1. Запуск VDbench

```powershell
Start-Process powershell `
  -ArgumentList "& 'C:\vdbench\vdbench.bat' -fworkload.txt"
```

---

## 2. Запуск экспортера

```bash
python -m src.main \
  --output-file output/flatfile.html \
  --stop-mode api
```

---

## 3. Выполнение нагрузки

Экспортер непрерывно читает output-файл VDbench и публикует метрики в Prometheus.

---

## 4. Внешняя остановка экспортера

```bash
curl -X POST \
  http://localhost:8080/shutdown
```

---

# Важные замечания

* Остановка экспортера выполняется корректно (graceful shutdown)
* Экспортер не завершает процесс VDbench
* Жизненный цикл VDbench управляется отдельно
* API предназначен для использования во внутренней сети или локальном окружении
* Аутентификация для API по умолчанию не реализована
