import os
import subprocess
import sys

# Конфигурация
PROJECT_NAME = "TTGTiSO-Test"
APPS = {
    "server": {"main": "server/main.py", "output": "TTGTiSO-Test-server"},
    "student": {"main": "client/main.py", "output": "TTGTiSO-Test-student"}
}

# Гарантируем, что patchelf и другие утилиты из venv/bin доступны Nuitka
exe_dir = os.path.dirname(sys.executable)
if exe_dir and exe_dir not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = exe_dir + os.pathsep + os.environ.get("PATH", "")

def run_command(cmd, raise_on_error=False):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Error executing command: {result.returncode}")
        if raise_on_error:
            raise RuntimeError(f"Command failed with code {result.returncode}")
        sys.exit(1)

def build_app_nuitka(app_name, config, raise_on_error=False):
    print(f"\n=== Building {app_name.upper()} (Nuitka) ===")

    # Базовые флаги Nuitka
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--plugin-enable=pyside6",
        "--include-package=cryptography",
        "--include-package=certifi",
        "--include-package=openpyxl",
        "--include-package-data=certifi",
        "--include-package-data=shared",
        "--assume-yes-for-downloads",
        f"--output-filename={config['output']}",
        f"--output-dir=dist/{app_name}",
        config['main']
    ]

    # Включаем ресурсы только если они существуют
    if os.path.exists("image.ico"):
        cmd.insert(-1, "--include-data-files=image.ico=image.ico")
    if os.path.exists("image.png"):
        cmd.insert(-1, "--include-data-files=image.png=image.png")
    if os.path.exists("shared/update_public_key.pem"):
        cmd.insert(-1, "--include-data-files=shared/update_public_key.pem=shared/update_public_key.pem")
    if os.path.exists("shared/icons"):
        cmd.insert(-1, "--include-data-dir=shared/icons=shared/icons")

    # Флаги для Windows
    if os.name == 'nt':
        cmd.extend([
            "--windows-disable-console",
            "--windows-icon-from-ico=image.ico"
        ])
    else:
        # Флаги для Linux
        if os.path.exists("image.png"):
            cmd.extend([
                "--linux-onefile-icon=image.png"
            ])
        else:
            print("Warning: image.png not found. Building Linux binary without embedded file icon.")

    run_command(cmd, raise_on_error=raise_on_error)

def build_app_pyinstaller(app_name, config):
    print(f"\n=== Building {app_name.upper()} (PyInstaller) ===")
    sep = ";" if os.name == "nt" else ":"
    root = os.path.dirname(os.path.abspath(__file__))

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        f"--name={config['output']}",
        "--onefile",
        f"--paths={root}",
        "--collect-all=shared",
        "--collect-all=cryptography",
        "--collect-all=certifi",
        f"--distpath={os.path.join(root, 'dist', app_name)}",
        f"--workpath={os.path.join(root, 'build', f'pyi_{app_name}')}",
        f"--specpath={os.path.join(root, 'build', f'spec_{app_name}')}",
    ]

    if app_name == "server":
        cmd.append("--collect-all=openpyxl")

    # Ресурсы
    if os.path.exists("image.ico"):
        cmd.extend([f"--add-data={os.path.join(root, 'image.ico')}{sep}."])
        if os.name == "nt":
            cmd.extend(["--icon=image.ico"])
    if os.path.exists("image.png"):
        cmd.extend([f"--add-data={os.path.join(root, 'image.png')}{sep}."])
    if os.path.exists("shared/update_public_key.pem"):
        cmd.extend([f"--add-data={os.path.join(root, 'shared', 'update_public_key.pem')}{sep}shared"])
    if os.path.exists("shared/icons"):
        cmd.extend([f"--add-data={os.path.join(root, 'shared', 'icons')}{sep}shared/icons"])

    if os.name == "nt":
        cmd.append("--windowed")

    cmd.append(config["main"])
    run_command(cmd)

def build_app(app_name, config, builder="auto"):
    if builder == "pyinstaller":
        build_app_pyinstaller(app_name, config)
    elif builder == "nuitka":
        build_app_nuitka(app_name, config)
    else:
        # Auto: попробуем Nuitka, если не получилось или нет заголовков - PyInstaller
        try:
            build_app_nuitka(app_name, config, raise_on_error=True)
        except Exception as e:
            print(f"\n⚠️ Сборка через Nuitka завершилась с ошибкой ({e}).")
            print(f"🔄 Переключаемся на PyInstaller для сборки {app_name}...\n")
            build_app_pyinstaller(app_name, config)

def ensure_build_dependencies():
    """Гарантирует установку cryptography, certifi, openpyxl перед компиляцией."""
    missing = []
    for pkg in ["cryptography", "certifi", "openpyxl"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if sys.platform.startswith("linux"):
        import shutil
        if not shutil.which("patchelf"):
            try:
                import patchelf  # noqa: F401
            except ImportError:
                missing.append("patchelf")

    if missing:
        print(f"📦 Установка недостающих зависимостей для сборщика: {', '.join(missing)}...")
        res = subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
        if res.returncode != 0:
            print(f"⚠️ Предупреждение: не удалось автоматически установить {missing}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Сборка TTGTiSO-Test (сервер и клиент)")
    parser.add_argument(
        "--builder",
        choices=["auto", "nuitka", "pyinstaller"],
        default="auto",
        help="Инструмент для сборки (по умолчанию auto)",
    )
    args = parser.parse_args()

    # Переходим в корень проекта если скрипт запущен из папки dist
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    # Проверяем и доустанавливаем зависимости (важно для CI/CD и чистых окружений)
    ensure_build_dependencies()

    # Создать image.png из image.ico для Linux (без GUI/X11 зависимостей)
    if os.path.exists("image.ico") and not os.path.exists("image.png"):
        print("Converting image.ico to image.png...")
        try:
            from PIL import Image
            with Image.open("image.ico") as img:
                img.save("image.png", "PNG")
            print("Successfully created image.png from image.ico using PIL!")
        except Exception as pil_err:
            try:
                from PySide6.QtGui import QImage
                img = QImage()
                if img.load("image.ico"):
                    if img.save("image.png", "PNG"):
                        print("Successfully created image.png from image.ico using PySide6!")
                    else:
                        print("Failed to save image.png via PySide6")
                else:
                    print("Failed to load image.ico via PySide6")
            except Exception as e:
                print(f"Warning during icon conversion: {e} (PIL also failed: {pil_err})")

    # Создаем папки если нет
    os.makedirs("dist", exist_ok=True)

    # Собираем оба приложения
    for app, cfg in APPS.items():
        build_app(app, cfg, builder=args.builder)

    print("\n=== BUILD COMPLETE ===")
    if os.name == 'nt':
        print("Now you can run Inno Setup with 'build/student_setup.iss' to create Windows Installer.")
    else:
        print("Now you can run 'sudo bash build/install.sh' to install Student Client on Linux.")

if __name__ == "__main__":
    main()
