import os
import sys
import subprocess
import shutil

# Конфигурация
PROJECT_NAME = "EduTest Pro"
APPS = {
    "server": {"main": "server/main.py", "output": "TTGTiSO-Test-server"},
    "student": {"main": "client/main.py", "output": "TTGTiSO-Test-student"}
}

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Error executing command: {result.returncode}")
        sys.exit(1)

def build_app(app_name, config):
    print(f"\n=== Building {app_name.upper()} ===")
    
    # Базовые флаги Nuitka
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--plugin-enable=pyside6",
        "--assume-yes-for-downloads",
        f"--output-filename={config['output']}",
        f"--output-dir=dist/{app_name}",
        config['main']
    ]
    
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

    run_command(cmd)

def main():
    # Переходим в корень проекта если скрипт запущен из папки dist
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

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
    if os.path.exists("dist"):
        # shutil.rmtree("dist") # Опционально: полная очистка
        pass
    os.makedirs("dist", exist_ok=True)
    
    # Собираем оба приложения
    for app, cfg in APPS.items():
        build_app(app, cfg)
        
    print("\n=== BUILD COMPLETE ===")
    if os.name == 'nt':
        print("Now you can run Inno Setup with 'build/student_setup.iss' to create Windows Installer.")
    else:
        print("Now you can run 'sudo bash build/install.sh' to install Student Client on Linux.")

if __name__ == "__main__":
    main()
