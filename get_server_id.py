import os
import paramiko
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Загрузка настроек из .env
load_dotenv()

# Настройки Google Sheets
spreadsheet_name = os.getenv("GOOGLE_SHEET_NAME")
service_account_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
worksheet_name = os.getenv("WORKSHEET_NAME", "Sheet1")
IP_COLUMN = int(os.getenv("IP_COLUMN", 3))
PASS_COLUMN = int(os.getenv("PASS_COLUMN", 4))
ID_COLUMN = int(os.getenv("ID_COLUMN", 5))

# Настройка авторизации
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, scope)
client = gspread.authorize(credentials)

# Открытие таблицы и листа
spreadsheet = client.open(spreadsheet_name)
worksheet = spreadsheet.worksheet(worksheet_name)

def get_machine_id(ip, password):
    """Получить machine-id с сервера через SSH"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username="root", password=password)

        stdin, stdout, stderr = ssh.exec_command("cat /etc/machine-id")
        machine_id = stdout.read().decode().strip()
        ssh.close()
        return machine_id
    except Exception as e:
        print(f"Ошибка подключения к серверу {ip}: {e}")
        return None

def update_sheet():
    """Обновить Google Sheet с machine-id"""
    start_row = int(input("С какой строки начать обработку? "))
    records = worksheet.get_all_values()
    updates = []

    for row_idx, row in enumerate(records, start=1):
        if row_idx < start_row:  # Пропуск строк до указанной
            continue

        ip = row[IP_COLUMN - 1] if len(row) >= IP_COLUMN else None
        password = row[PASS_COLUMN - 1] if len(row) >= PASS_COLUMN else None
        existing_id = row[ID_COLUMN - 1] if len(row) >= ID_COLUMN else None

        if ip and password and not existing_id:
            print(f"Обработка сервера: {ip}")
            machine_id = get_machine_id(ip, password)

            if machine_id:
                updates.append((row_idx, ID_COLUMN, machine_id))
                print(machine_id)
            else:
                print(f"Не удалось получить ID сервера {ip}")

    if updates:
        cells = worksheet.range(start_row, ID_COLUMN, len(records), ID_COLUMN)
        for update, cell in zip(updates, cells):
            row_idx, col_idx, value = update
            cell.value = value
        worksheet.update_cells(cells)

if __name__ == "__main__":
    update_sheet()
