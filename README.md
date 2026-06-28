# vdbench_exporter

Prometheus-экспортёр метрик VDbench. Читает `flatfile.html` в реальном времени и публикует метрики IOPS, латентности и пропускной способности.

Поддерживает онлайн-режим (слежение за живым файлом) и офлайн-режим (однократный импорт готового файла).

---

## Установка

```bash
pip install -r requirements.txt
```

---

## Запуск

### Онлайн-режим

Экспортёр следит за `flatfile.html` по мере того, как VDbench дописывает новые строки.

```bash
python -m src.main --output-file output/flatfile.html
```

Метрики доступны на `http://localhost:8000/metrics`.

### Офлайн-режим

Однократный импорт уже готового файла. После обработки всех строк экспортёр завершается.

```bash
python -m src.main \
  --input-file output/flatfile.html \
  --stop-mode api
```

---

## Аргументы

| Аргумент          | По умолчанию | Описание                                                              |
|-------------------|:------------:|-----------------------------------------------------------------------|
| `--output-file`   |              | Путь к `flatfile.html` VDbench. Обязателен если не указан `--input-file` |
| `--input-file`    |              | Путь к файлу для офлайн-импорта. Если указан — запускается офлайн-режим |
| `--port`          | `8000`       | Порт для scrape-эндпоинта `/metrics`                                  |
| `--api-port`      | `8080`       | Порт Control API                                                      |
| `--stop-mode`     | `api`        | Режим остановки: `timer`, `api`                                       |
| `--duration`      |              | Время работы в секундах (только для `--stop-mode timer`)              |
| `--read-polling`  | `0.2`        | Как часто опрашивать flatfile на новые строки (секунды)               |
| `--polling`       | `5`          | Интервал отправки метрик в Pushgateway (секунды)                      |
| `--push-gateway`  |              | URL Prometheus Pushgateway для активной отправки метрик (опционально). Если не указан — экспортёр работает только в режиме scrape |
| `--job-name`      | `vdbench`    | Имя job при отправке метрик в Pushgateway                             |
| `--trace-file`    |              | Путь к файлу трассировки обработанных строк (JSONL)                   |
| `--prometheus-url`|              | URL Prometheus для remote write в офлайн-режиме (например `http://localhost:9090`) |
| `--offline-step-ms`| `1000`      | Шаг между временными метками строк при офлайн remote write (мс)       |
| `--offline-batch-size`| `100`   | Количество строк в одном remote write запросе (офлайн-режим)          |
| `--log-level`     | `INFO`       | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR`              |

### Режимы остановки (`--stop-mode`)

| Режим   | Поведение                                                        |
|---------|------------------------------------------------------------------|
| `timer` | Останавливается через `--duration` секунд                        |
| `api`   | Останавливается по команде `POST /shutdown`                      |

---

## Офлайн-режим и Prometheus

В офлайн-режиме экспортёр может отправлять все строки из flatfile в Prometheus через remote write API (`--prometheus-url`).

### Временные метки

Исторические временные метки из flatfile не используются — Prometheus 3.x не принимает данные из прошлого без специальной настройки. Вместо этого экспортёр генерирует инкрементальные временные метки начиная с текущего момента: каждая следующая строка получает timestamp на `--offline-step-ms` миллисекунд больше предыдущей.

Пример: при 100 строках и `--offline-step-ms 1000` временной ряд растянется на ~100 секунд от текущего момента.

### Требования к Prometheus

Контейнер должен быть запущен с флагом `--web.enable-remote-write-receiver`:

```powershell
docker run -d `
  --name inspiring_vaughan `
  -p 9090:9090 `
  -v "C:\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml" `
  prom/prometheus `
  --config.file=/etc/prometheus/prometheus.yml `
  --storage.tsdb.path=/prometheus `
  --web.enable-remote-write-receiver
```

### Пример запуска с remote write

```bash
python -m src.main \
  --input-file output/flatfile.html \
  --stop-mode api \
  --prometheus-url http://localhost:9090
```

---

## Control API

При запуске экспортёр поднимает HTTP API на `--api-port` (по умолчанию `8080`).

### GET /health

Состояние экспортёра.

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
  "uptime_seconds": 153,
  "last_raw_line": "3 3 0 3000 30.5 4096 3.2 3.2 0.0 0 0 0 0 0 0",
  "last_metrics": {
    "iops": 3000.0,
    "latency": 3.2,
    "throughput": 31981568.0
  },
  "offline_completed": false
}
```

| Поле                        | Описание                                               |
|-----------------------------|--------------------------------------------------------|
| `status`                    | `ok` или `degraded` (если метрики не обновлялись >30с) |
| `reader_running`            | Активно ли чтение файла                                |
| `shutdown_requested`        | Получен ли сигнал остановки                            |
| `output_file_exists`        | Существует ли `output-file`                            |
| `last_metrics_update`       | Unix-timestamp последнего обновления метрик            |
| `seconds_since_last_update` | Секунд с последнего обновления                         |
| `mode`                      | Текущий режим остановки                                |
| `uptime_seconds`            | Время работы экспортёра в секундах                     |
| `last_raw_line`             | Последняя обработанная строка из flatfile              |
| `last_metrics`              | Последние значения метрик                              |
| `offline_completed`         | Завершён ли офлайн-импорт                              |

### POST /shutdown

Остановка экспортёра (только в режиме `--stop-mode api`).

```bash
curl -X POST http://localhost:8080/shutdown
```

Пример ответа:

```json
{
  "status": "stopping"
}
```

---

## Публикуемые метрики

| Метрика              | Описание                  |
|----------------------|---------------------------|
| `vdbench_iops`       | IOPS                      |
| `vdbench_latency`    | Латентность (мс)          |
| `vdbench_throughput` | Пропускная способность (байт/с) |