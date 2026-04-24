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