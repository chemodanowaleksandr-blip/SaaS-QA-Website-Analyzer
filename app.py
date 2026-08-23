import streamlit as st
import time
import sqlite3
import pandas as pd
from core_worker import analyze_website

# 1. Инициализация базы данных SQLite
DB_FILE = "qa_history.db"

def init_db():
    """Создает таблицу истории, если её еще нет"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            url TEXT,
            status_code INTEGER,
            load_time REAL,
            links_count INTEGER,
            verdict TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_history(url, status, load_time, links, verdict):
    """Сохраняет результаты теста в базу данных"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO audit_history (timestamp, url, status_code, load_time, links_count, verdict)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (current_time, url, status, load_time, links, verdict))
    conn.commit()
    conn.close()

def get_history():
    """Вытаскивает всю историю из базы для отображения"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT timestamp as 'Дата', url as 'URL', status_code as 'Статус HTTP', load_time as 'Время (сек)', links_count as 'Ссылки', verdict as 'Вердикт' FROM audit_history ORDER BY id DESC", conn)
    conn.close()
    return df

# Запускаем создание БД при старте приложения
init_db()

# Настраиваем внешний вид страницы нашего SaaS-сервиса
st.set_page_config(page_title="SaaS QA Website Analyzer", page_icon="🤖", layout="centered")

st.title("🤖 SaaS QA Automated Website Analyzer")
st.write("Вставьте ссылку на любой сайт ниже, чтобы запустить мгновенный автоматический QA-аудит.")

# Поле для ввода URL-адреса клиентом
target_url = st.text_input("Введите URL сайта для проверки:", placeholder="https://example.com")

if st.button("🚀 Запустить QA-аудит"):
    if not target_url:
        st.error("Пожалуйста, введите корректный URL-адрес!")
    else:
        with st.spinner("Робот сканирует страницы и проверяет ссылки... Подождите..."):
            try:
                # Вызываем наш основной движок из core_worker.py
                result = analyze_website(target_url)
                
                st.success("🎉 Аудит успешно завершен!")
                
                # Выводим основные метрики в красивых карточках
                col1, col2, col3 = st.columns(3)
                col1.metric("Статус ответа", f"HTTP {result['status_code']}")
                col2.metric("Скорость ответа", f"{result['load_time_sec']} сек")
                col3.metric("Проверено ссылок", result['total_links_checked'])
                
                # Выводим итоговый вердикт с цветовым выделением
                if "Passed" in result["verdict"]:
                    st.info(f"🏆 Итоговый вердикт: **{result['verdict']}**")
                else:
                    st.warning(f"⚠️ Итоговый вердикт: **{result['verdict']}**")
                
                # Блок вывода битых ссылок
                st.subheader("🔗 Отчет по внутренним ссылкам")
                if result["broken_links"]:
                    st.error(f"Обнаружено битых ссылок: {len(result['broken_links'])}")
                    for idx, broken in enumerate(result["broken_links"], 1):
                        st.write(f"🛑 **{idx}.** Код [{broken['status']}] — {broken['url']}")
                else:
                    st.success("✅ Отлично! Все проверенные внутренние ссылки работают корректно.")
                
                # ТУТ ДОПИСАНО: Сохраняем результаты в нашу БД SQLite
                save_to_history(
                    target_url, 
                    result['status_code'], 
                    result['load_time_sec'], 
                    result['total_links_checked'], 
                    result['verdict']
                )
                    
            except Exception as e:
                st.error(f"Произошла непредвиденная ошибка при анализе: {e}")

# ТУТ ДОПИСАНО: Выводим таблицу истории из БД в самом низу страницы
st.markdown("---")
st.subheader("📊 История последних проверок (из БД)")
history_df = get_history()

if not history_df.empty:
    # Выводим данные в виде интерактивной таблицы Streamlit
    st.dataframe(history_df, use_container_width=True)
else:
    st.write("История пока пуста. Запустите первый тест, чтобы наполнить базу данных!")

st.caption("© 2026 SaaS QA Analyzer. Powered by Python, Streamlit & SQLite.")
