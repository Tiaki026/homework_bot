# import subprocess

# # Активация виртуального окружения
# venv_activate = r"D:\Dev\homework_bot\venv\Scripts\activate"

# # Команда для запуска бота (замените на вашу команду)
# bot_command = "python D:\Dev\homework_bot\homework.py"

# # Запуск активации виртуального окружения и бота
# subprocess.Popen(["cmd.exe", "/k", venv_activate, "&", bot_command], shell=True)

import subprocess

# Путь к интерпретатору Python внутри виртуального окружения
python_path = "D:\\Dev\\homework_bot\\venv\\Scripts\\python.exe"

# Путь к скрипту внутри виртуального окружения
bot_script = "D:\\Dev\\homework_bot\\homework.py"

# Запуск скрипта внутри активированного виртуального окружения
subprocess.run([python_path, bot_script], shell=True)
