# Changelog

Все значимые изменения проекта документируются здесь.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект использует [семантическое версионирование](https://semver.org/lang/ru/).

## [Unreleased]

### 🔐 Security
- **Подпись авто-обновлений (Ed25519).** Сервер подписывает каждый рассылаемый бинарник; клиент отказывается запускать обновление с отсутствующей или невалидной подписью. См. `shared/security.py`, `scripts/sign_update.py`, `scripts/generate_signing_keys.py`.
- **Path traversal в `@image:` запрещён.** Парсер теперь нормализует путь и не выходит за пределы директории с тестом.
- **`MAX_MESSAGE_SIZE` снижен** с 500 МБ до 64 МБ — закрывает простой DoS на стороне сервера и клиента.
- **Verified TLS.** Обращение к GitHub API больше не использует `ssl._create_unverified_context()`. Корневые сертификаты берутся из пакета `certifi`.

### ✨ Added
- Unit-тесты на `shared/parser.py` и `calculate_score` (`tests/`).
- CI-workflow `.github/workflows/ci.yml` — `ruff` + `pytest` на каждый PR.
- `pyproject.toml` с настройками `pytest` и `ruff`.
- `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
- `requirements.txt` и `requirements-dev.txt` с pinned-зависимостями.

### 🧹 Changed
- Из репозитория удалены случайно закоммиченные временные файлы (`promt.txt`, `test_edited.txt` 5 МБ, `фыафыафы.txt`).

## [1.3.7] — 2025-05

Базовая версия до начала аудита. История релизов: <https://github.com/uiper123/tgtgtess/releases>.
