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
        ])
    else:
        # Флаги для Linux
        pass # Можно добавить иконку если нужно

    run_command(cmd)

def main():
    # Переходим в корень проекта если скрипт запущен из папки dist
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

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
