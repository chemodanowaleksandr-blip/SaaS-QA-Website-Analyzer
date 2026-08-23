import asyncio
import httpx
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import time
import sqlite3

# 1. Инициализация базы данных SQLite (Шаг 4 из шпаргалки — Монетизация/История)
DB_FILE = "qa_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            status TEXT,
            links_found INTEGER,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_history(url, status, links_count):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scan_history (url, status, links_found, timestamp) VALUES (?, ?, ?, ?)",
        (url, status, links_count, time.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

# 2. Асинхронный движок парсера (Шаг 1 из шпаргалки — Скорость и обход блокировок)
async def analyze_website(url: str):
    # Маскируемся под обычный браузер, чтобы сайты нас не блочили
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Используем асинхронный httpx клиент с таймаутом
    async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            
            if response.status_code != 200:
                return {"status": "Failed", "error": f"Ошибка со стороны сайта: {response.status_code}", "links": []}
                
            # Парсим HTML через BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Собираем все внутренние и внешние ссылки для QA-аудита
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                text = a_tag.text.strip() or "[Изображение/Без текста]"
                links.append({"Текст ссылки": text, "URL": href})
                
            return {
                "status": "Passed",
                "error": None,
                "links": links
            }
            
        except Exception as e:
            return {"status": "Failed", "error": f"Не удалось подключиться: {str(e)}", "links": []}

# 3. Веб-интерфейс на Streamlit (Шаг 2 из шпаргалки — SaaS платформа)
def main():
    st.set_page_config(page_title="SaaS QA Website Analyzer", page_icon="🔍", layout="wide")
    init_db()
    
    st.title("🔍 SaaS QA Website Analyzer — Стартап Движок")
    st.caption("Автоматический аудит ссылок, структуры и доступности веб-сайтов в реальном времени.")
    
    # Боковая панель (Сидбар) с историей проверок
    st.sidebar.header("📋 История проверок")
    conn = sqlite3.connect(DB_FILE)
    try:
        df_history = pd.read_sql_query("SELECT url, status, timestamp FROM scan_history ORDER BY id DESC LIMIT 10", conn)
        if not df_history.empty:
            st.sidebar.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.sidebar.info("История пока пуста. Запустите первый скан!")
    except Exception:
        st.sidebar.error("Ошибка загрузки истории.")
    finally:
        conn.close()

    # Главная зона интерфейса
    target_url = st.text_input("Введите URL сайта для автоматического QA-тестирования:", placeholder="https://example.com")
    
    if st.button("🚀 Начать автоматический тест", type="primary"):
        if not target_url:
            st.warning("Пожалуйста, укажите адрес сайта!")
            return
            
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
            
        st.info(f"Запускаем асинхронный обход для: {target_url}...")
        
        # Создаем анимацию загрузки (спиннер)
        with st.spinner("Движок парсера собирает данные..."):
            start_time = time.time()
            
            # Запускаем асинхронную функцию внутри синхронного Streamlit
            result = asyncio.run(analyze_website(target_url))
            
            end_time = time.time()
            
        # Вывод результатов теста
        if result["status"] == "Passed":
            st.success(f"✅ ОТЧЕТ О ТЕСТИРОВАНИИ — Проверка пройдена за {end_time - start_time:.2f} сек.")
            
            # Сохраняем в базу данных
            save_to_history(target_url, "Passed", len(result["links"]))
            
            # Метрики
            col1, col2 = st.columns(2)
            col1.metric("Статус сайта", "200 OK")
            col2.metric("Найдено уникальных ссылок", len(result["links"]))
            
            # Вывод таблицы ссылок
            if result["links"]:
                st.subheader("🔗 Найденные элементы и ссылки на странице:")
                df_links = pd.DataFrame(result["links"])
                st.dataframe(df_links, use_container_width=True)
                
                # Кнопка скачивания отчета в CSV (Фишка для коммерческой версии)
                csv = df_links.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Скачать полный отчет в CSV",
                    data=csv,
                    file_name="qa_site_report.csv",
                    mime="text/csv",
                )
        else:
            st.error(f"❌ ТЕСТ ПРОВАЛЕН. {result['error']}")
            save_to_history(target_url, "Failed", 0)

if __name__ == "__main__":
    main()
