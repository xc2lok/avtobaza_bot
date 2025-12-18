import telebot
from io import BytesIO

TOKEN = "8193635388:AAGLbfLfIx5oLgOPa2EPOULjVHEMMc12gN4"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋\nПришлите вашу базу в формате .txt (как документ), и я верну обработанную базу файлом."
    )

@bot.message_handler(content_types=['document'])
def handle_document(message):
    # Принимаем только .txt
    if not message.document.file_name.lower().endswith('.txt'):
        bot.reply_to(message, "Пожалуйста, отправь файл именно .txt (как документ).")
        return

    try:
        # Скачиваем файл
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Декодируем текст
        text = downloaded_file.decode('utf-8', errors='replace')

        # Нормализуем переносы строк (на всякий случай)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')

        # Находим индекс разделителя (любая строка, где есть _____)
        separator_idx = next((i for i, line in enumerate(lines) if '_____' in line), None)
        if separator_idx is None:
            bot.reply_to(message, "Не найден разделитель '_____'. Проверь файл.")
            return

        before = lines[:separator_idx]
        after = lines[separator_idx + 1:]

        dir_keywords = [
            'Заведующий', 'Директор', 'Дир', 'Главный врач',
            'Исполняющий обязанности главного врача', 'Исполняющий обязанности директора',
            'И.о. главного врача', 'И.о. директора'
        ]
        zam_keywords = [
            'Заместитель', 'Зам', 'Зам. директора', 'Зам. главного врача'
        ]

        # Парсим до разделителя: директор и зам
        dir_name = None
        zam_name = None

        for i, line in enumerate(before):
            stripped_lower = line.strip().lower()

            if any(kw.lower() in stripped_lower for kw in dir_keywords):
                if i + 1 < len(before):
                    next_line = before[i + 1].strip()
                    dir_name = ' '.join(next_line.split()[:3])  # ФИО

            elif any(kw.lower() in stripped_lower for kw in zam_keywords):
                if i + 1 < len(before):
                    next_line = before[i + 1].strip()
                    zam_name = ' '.join(next_line.split()[:3])  # ФИО

        if not dir_name or not zam_name:
            bot.reply_to(
                message,
                "Не найдены 'Директор' или 'Зам' в части ДО разделителя.\n"
                "Проверь метки (например: 'Директор', 'Заведующий', 'Заместитель' и т.п.)."
            )
            return

        # Парсим после разделителя: фейки и обычные люди
        people = []
        i = 0
        while i < len(after):
            name_line = after[i].strip()

            if not name_line:
                i += 1
                continue

            # ожидаем, что следующая строка — контакт (или пусто)
            contact_line = after[i + 1].strip() if i + 1 < len(after) else ''

            # очищаем контакт: удаляем 't.me/' и хвост 'фейк...'
            cleaned_contact = contact_line.replace('t.me/', '').split(' фейк')[0].strip()

            if 'фейк' in contact_line.lower():
                people.append(('fake', name_line, cleaned_contact))
            else:
                people.append(('normal', name_line, cleaned_contact))

            i += 2

        fakes = [p for p in people if p[0] == 'fake']
        normals = [p for p in people if p[0] == 'normal']

        fake1 = fakes[0][1] if fakes else ''
        fake2 = fakes[1][1] if len(fakes) > 1 else ''

        # ====== СБОРКА ВЫХОДА С ТОЧНЫМИ ПУСТЫМИ СТРОКАМИ КАК В ПРИМЕРЕ ======
        out_lines = [
            "Директор",
            dir_name,
            "",               # пустая строка как в примере

            "Зам",
            zam_name,
            "",               # пустая строка

            "актер 1",
            fake1,
            "",               # пустая строка

            "актер 2",
            fake2,
            "_____________________________________",
            "",               # пустая строка после линии
        ]

        for _, name_date, phone in normals:
            out_lines.append(name_date)
            out_lines.append(phone)
            out_lines.append("")  # пустая строка между записями

        # В конце пример заканчивается на ...+телефон " (без обязательной пустой строки),
        # поэтому убираем последнюю пустую строку, если она лишняя:
        if out_lines and out_lines[-1] == "":
            out_lines.pop()

        output = "\n".join(out_lines)
        # ===================================================================

        # Отдаём результат ФАЙЛОМ .txt с тем же именем, что у входного файла
        out_bytes = output.encode('utf-8')
        bio = BytesIO(out_bytes)
        bio.name = message.document.file_name
        bio.seek(0)

        bot.send_document(
            chat_id=message.chat.id,
            document=bio,
            caption="Готово ✅ Ваша обработанная база во вложении."
        )

    except Exception as e:
        bot.reply_to(message, f"Ошибка обработки файла: {str(e)}")

bot.infinity_polling()
