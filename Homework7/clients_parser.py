# Чтение файла
def read_file():
    with open('web_clients_correct.csv', 'r', encoding='utf-8') as f:
        return f.readlines()

# Преобразование данных
def process_data(lines):
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split(',')

        # Проверяем, что в строке достаточно данных
        if len(parts) >= 7:
            client_data = {
                'name': parts[0].strip(),
                'device': parts[1].strip(),
                'browser': parts[2].strip(),
                'gender': parts[3].strip(),
                'age': parts[4].strip(),
                'bill': parts[5].strip(),
                'region': parts[6].strip()
            }
            result.append(client_data)
    return result

# Преобразование пола
def convert_gender(gender):
    gender_map = {
        "female": "женского",
        "male": "мужского"
    }
    return gender_map.get(gender, "неизвестного")

# Преобразование устройства
def convert_device(device):
    device_map = {
        "mobile": "мобильного",
        "tablet": "планшета",
        "laptop": "ноутбука",
        "desktop": "настольного компьютера"
    }
    return device_map.get(device, "устройства")

# Формирование описания
def create_description(client):
    # Преобразуем данные
    gender_text = convert_gender(client['gender'])
    device_text = convert_device(client['device'])

    # Определяем глагол по полу
    verb = "совершил(а)"
    if client['gender'] == "female":
        verb = "совершила"
    elif client['gender'] == "male":
        verb = "совершил"

    # Обрабатываем регион
    region_text = client['region'] if client['region'] != "-" else "неизвестен"

    # Формируем описание
    if client['device'] == "mobile":
        device_info = f"с мобильного браузера {client['browser']}"
    else:
        device_info = f"с {device_text} {client['browser']}"

    description = (f"Пользователь {client['name']} {gender_text} пола, {client['age']} лет "
                   f"{verb} покупку на {client['bill']} у.е. {device_info}. "
                   f"Регион, из которого совершалась покупка: {region_text}.")

    return description

# Запись в файл
def write_to_file(descriptions):
    with open('descriptions.txt', 'w', encoding='utf-8') as f:
        for i, desc in enumerate(descriptions):
            f.write(desc)
            # Добавляем переносы только между записями, не после последней
            if i < len(descriptions) - 1:
                f.write("\n\n")

# Главная функция
def main():
    try:
        # Читаем файл
        lines = read_file()

        # Проверяем, что файл не пустой
        if not lines:
            print("Файл пустой или не найден")
            return

        # Обрабатываем данные
        clients = process_data(lines)

        # Проверяем, что есть данные для обработки
        if not clients:
            print("Нет данных для обработки")
            return

        # Создаем описания
        all_descriptions = []
        for client in clients:
            desc = create_description(client)
            all_descriptions.append(desc)

        # Записываем в файл
        write_to_file(all_descriptions)

        # Выводим информацию о результате
        print(f"Обработаны записи в кол-ве: {len(clients)} шт.")
        print("Файл успешно сохранен!")

    except FileNotFoundError:
        print("Ошибка: файл не найден")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

# Запускаем программу
main()