import io
import pandas as pd


def generate_excel_report(urls_data):
    """Принимает список словарей с данными ссылок и возвращает готовый к

    скачиванию байтовый буфер Excel-файла.
    """
    # 1. Переводим данные в таблицу Pandas
    df = pd.DataFrame(urls_data)

    # 2. Создаем буфер в памяти
    buffer = io.BytesIO()

    # 3. Записываем данные в Excel без сохранения на жесткий диск сервера
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Аудит Ссылок")

    # 4. Сбрасываем указатель буфера на начало и возвращаем его
    buffer.seek(0)
    return buffer
