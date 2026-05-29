# Как контрибьютить

Спасибо, что хотите помочь TTGTiSO-Test! 🎓

## Быстрый старт

```bash
git clone https://github.com/uiper123/tgtgtess.git
cd tgtgtess
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Запуск

```bash
# Сервер преподавателя
python server/main.py

# Клиент студента (в другом терминале)
python client/main.py

# Или оба сразу (Linux/macOS):
./run_test.sh
```

## Тесты и линт

```bash
pytest                         # запустить все тесты
pytest --cov=shared --cov=server --cov=client    # с покрытием
ruff check .                   # линт
ruff format .                  # автоформат
```

CI прогоняет всё это автоматически в `.github/workflows/ci.yml` на каждый PR.

## Структура проекта

| Каталог | Что внутри |
|---|---|
| `shared/` | Чистый pure-python код: парсер, протокол, версии, утилиты безопасности. |
| `server/` | Сервер преподавателя (Qt UI + `QTcpServer`). |
| `client/` | Клиент студента (киоск-режим + `QTcpSocket`). |
| `tests/` | Unit-тесты на pytest. |
| `scripts/` | Сервисные CLI: генерация ключей, подпись обновлений. |
| `build/` | Конфиги Inno Setup и shell-скрипты сборки. |

## Правила PR

1. **Одна фича — один PR.** Не смешивайте багфикс, фичу и рефакторинг.
2. **Тесты обязательны** для любой логики в `shared/` (парсер, скоринг, безопасность). Для UI достаточно скриншотов.
3. **Не ломайте сетевой протокол** без бампа `shared/version.py` и записи в `CHANGELOG.md`.
4. **Сообщения коммитов** — в Conventional Commits: `feat(server): ...`, `fix(parser): ...`, `chore: ...`. Это упрощает changelog.

## Безопасность

Если нашли уязвимость, **не публикуйте её в issue** — см. [`SECURITY.md`](SECURITY.md).
