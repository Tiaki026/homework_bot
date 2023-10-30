import subprocess

# Путь к интерпретатору Python внутри виртуального окружения
python_path = "D:\\Dev\\homework_bot\\venv\\Scripts\\python.exe"

# Путь к скрипту внутри виртуального окружения
bot_script = "D:\\Dev\\homework_bot\\homework.py"

# Запуск скрипта внутри активированного виртуального окружения
subprocess.run([python_path, bot_script], shell=True)
