# Тесты vdbench_exporter

## Структура

```
tests/
├── unit/                    # Юнит-тесты (без внешних зависимостей)
├── offline_integration/     # Интеграционные тесты офлайн-режима (subprocess)
├── integration/             # Lab-тесты (требуют живого окружения)
├── perfomance/              # Микробенчмарки (без внешних зависимостей)
└── config.py                # Конфигурация через переменные окружения
```

---

## Юнит-тесты

Не требуют запущенного экспортёра, VDbench или Prometheus.

```
pytest tests/unit/ -m "not integration and not performance"
```

---

## Офлайн-интеграционные тесты

Поднимают экспортёр как subprocess и проверяют полный пайплайн в офлайн-режиме.
Не требуют VDbench или Prometheus.

```
pytest tests/offline_integration/
```

### Remote write в офлайн-режиме

Если нужно проверить отправку метрик в Prometheus через remote write (`--prometheus-url`),
контейнер Prometheus должен существовать и быть создан с флагом `--web.enable-remote-write-receiver`:

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

Без этого флага remote write недоступен и экспортёр будет получать `404` на `/api/v1/write`.

Офлайн-интеграционные тесты (`tests/offline_integration/`) remote write не проверяют —
они работают только с локальными Gauge-метриками. Remote write покрыт юнит-тестом
`test_run_offline_calls_remote_write` с моком.

---

## Микробенчмарки

Измеряют задержку обработки строк внутри процесса без сетевого взаимодействия.
Не требуют внешних сервисов.

```
pytest tests/perfomance/ -m performance -s
```

Пороги по умолчанию рассчитаны под `read_polling=0.05`.
Переопределяются через переменные окружения:

| Переменная                    | По умолчанию | Описание              |
|-------------------------------|--------------|-----------------------|
| `TEST_MICRO_P95_LATENCY_SEC`  | `0.05`       | P95 задержки обработки|
| `TEST_TRACE_WAIT_TIMEOUT_SEC` | `10`         | Таймаут сбора трейса  |

---

## Lab-тесты (интеграция с живым окружением)

Требуют запущенного окружения: экспортёр + VDbench + Prometheus.

### Предварительные требования

Запуск лабы производится автоматически через `tests/integration/conftest.py`.
Для этого необходимо:

- **VDbench** — указать путь до исполняемого файла через переменную окружения `TEST_VDBENCH`
  (по умолчанию `C:\Users\varia\Downloads\vdbench50407\vdbench50407\vdbench.bat`)
- **Docker** — для запуска контейнеров Prometheus и Grafana.
  Grafana не используется тестами напрямую, но поднимается вместе с лабой для визуального мониторинга.
- **Образы** `prom/prometheus` и `grafana/grafana` должны быть доступны локально или в registry.
  Названия контейнеров задаются через переменные окружения `TEST_PROMETHEUS_CONTAINER_NAME`
  (по умолчанию `inspiring_vaughan`) и `TEST_GRAFANA_CONTAINER_NAME` (по умолчанию `grafana`)

После старта conftest поднимает окружение, запускает экспортёр и ждёт готовности всех сервисов.

### Запуск

```
pytest tests/integration/ -m integration -s
```

Тесты пропускаются автоматически если экспортёр недоступен.

### Пороги производительности

Рассчитаны под `--read-polling 0.05` на Windows:

| Переменная                          | По умолчанию | Описание                    |
|-------------------------------------|--------------|-----------------------------|
| `TEST_LAB_AVG_DETECTION_LATENCY_SEC`| `0.25`       | Средняя задержка обнаружения|
| `TEST_LAB_P95_DETECTION_LATENCY_SEC`| `0.50`       | P95 задержки обнаружения    |
| `TEST_LAB_SAMPLE_WAIT_TIMEOUT_SEC`  | `60`         | Таймаут сбора 30 записей    |

### Конфигурация через переменные окружения

| Переменная                    | По умолчанию                    |
|-------------------------------|---------------------------------|
| `TEST_EXPORTER_METRICS_URL`   | `http://localhost:8000/metrics` |
| `TEST_EXPORTER_HEALTH_URL`    | `http://localhost:8080/health`  |
| `TEST_EXPORTER_SHUTDOWN_URL`  | `http://localhost:8080/shutdown`|
| `TEST_PROMETHEUS_URL`         | `http://localhost:9090`         |
| `TEST_OUTPUT_DIR`             | `output`                        |

---

## Запуск всех тестов кроме lab

```
pytest tests/unit/ tests/offline_integration/ tests/perfomance/ -s
```

## Примечания

- Тесты производительности чувствительны к таймерам Windows (~15 мс джиттер).
  При `read_polling=0.05` (дефолт) P95 detection latency достигает 0.5–0.8 с — это нормально.
  Для воспроизводимых результатов запускай экспортёр с `--read-polling 0.05`.
- Lab-тесты читают реальный `output/exporter_trace.jsonl` и `output/flatfile.html`,
  которые заполняются автоматически после старта окружения через conftest.