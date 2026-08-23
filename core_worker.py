import asyncio
import httpx
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import time
import sqlite3
from urllib.parse import urljoin, urlparse

# 1. Инициализация базы данных SQLite
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

# 2. Универсальный асинхронный движок парсера (Стабильная версия)
async def analyze_website(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    # Мы убрали http2=True, теперь код запустится на любой машине без ошибок расширений
    async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                return {"status": "Failed", "error": f"HTTP Error: {response.status_code}", "links": []}
                
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = str(response.url)
            
            links = []
            seen_urls = set()
            
            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"].strip()
                if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                
                full_url = urljoin(base_url, raw_href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                is_internal = urlparse(full_url).netloc == urlparse(base_url).netloc
                links.append({
                    "text": a_tag.text.strip() or "[No Text / Icon]",
                    "url": full_url,
                    "is_internal": is_internal
                })
                
            return {"status": "Passed", "error": None, "links": links}
        except Exception as e:
            return {"status": "Failed", "error": str(e), "links": []}

# 3. Веб-интерфейс
def main():
    st.set_page_config(page_title="Global SaaS QA Website Analyzer", page_icon="🔍", layout="wide")
    init_db()
    
    lang = st.sidebar.selectbox("🌐 Language / Язык", ["Русский", "English"])
    
    t = {
        "Русский": {
            "title": "🔍 Глобальный SaaS QA Анализатор Сайтов",
            "subtitle": "Профессиональный инструмент автоматического аудита ссылок и структуры веб-ресурсов для СНГ и международных рынков.",
            "history": "📋 История проверок",
            "history_empty": "История пуста. Проверьте первый сайт!",
            "placeholder": "Введите URL сайта (например, mysite.am или site.com):",
            "button": "🚀 Запустить автоматический аудит",
            "warning": "Пожалуйста, укажите адрес сайта!",
            "info": "Анализируем цель: ",
            "spinner": "Движок обрабатывает элементы веб-страницы...",
            "success": "✅ АУДИТ ЗАВЕРШЕН — Обработано за {:.2f} сек.",
            "metric_status": "Статус ответа",
            "metric_links": "Найдено уникальных ссылок",
            "table_title": "🔗 Сканированные элементы и таблица маршрутизации:",
            "col_text": "Элемент (Текст)",
            "col_url": "Полный URL адрес",
            "col_type": "Тип ссылки",
            "type_int": "Внутренняя",
            "type_ext": "Внешняя",
            "download": "📥 Скачать полный отчет в CSV",
            "failed": "❌ АУДИТ ПРОВАЛЕН. "
        },
        "English": {
            "title": "🔍 Global SaaS QA Website Analyzer",
            "subtitle": "Professional automated QA tool for testing website structure, internal links, and compliance.",
            "history": "📋 Scan History",
            "history_empty": "No scans yet. Try your first URL!",
            "placeholder": "Enter website URL (e.g., mysite.am or site.com):",
            "button": "🚀 Run Automated Audit",
            "warning": "Please enter a valid URL!",
            "info": "Analyzing target: ",
            "spinner": "Processing webpage elements...",
            "success": "✅ AUDIT COMPLETE — Processed in {:.2f} seconds.",
            "metric_status": "Response Status",
            "metric_links": "Unique Links Found",
            "table_title": "🔗 Scanned Web Elements & Routing Table:",
            "col_text": "Element (Text)",
            "col_url": "Full URL Address",
            "col_type": "Link Type",
            "type_int": "Internal",
            "type_ext": "External",
            "download": "📥 Download Full Report (CSV)",
            "failed": "❌ AUDIT FAILED. "
        }
    }[lang]

    st.title(t["title"])
    st.caption(t["subtitle"])
    
    st.sidebar.header(t["history"])
    conn = sqlite3.connect(DB_FILE)
    try:
        df_history = pd.read_sql_query("SELECT url, status, timestamp FROM scan_history ORDER BY id DESC LIMIT 10", conn)
        if not df_history.empty:
            st.sidebar.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.sidebar.info(t["history_empty"])
    except Exception:
        st.sidebar.error("DB error.")
    finally:
        conn.close()

    user_input = st.text_input(t["placeholder"], placeholder="example.com")
    
    if st.button(t["button"], type="primary"):
        if not user_input:
            st.warning(t["warning"])
            return
            
        target_url = user_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
            
        st.info(f"{t['info']} {target_url}...")
        
        with st.spinner(t["spinner"]):
            start_time = time.time()
            result = asyncio.run(analyze_website(target_url))
            end_time = time.time()
            
        if result["status"] == "Passed":
            st.success(t["success"].format(end_time - start_time))
            save_to_history(target_url, "Passed", len(result["links"]))
            
            col1, col2 = st.columns(2)
            col1.metric(t["metric_status"], "200 OK")
            col2.metric(t["metric_links"], len(result["links"]))
            
            if result["links"]:
                st.subheader(t["table_title"])
                
                formatted_links = []
                for link in result["links"]:
                    formatted_links.append({
                        t["col_text"]: link["text"][:50],
                        t["col_url"]: link["url"],
                        t["col_type"]: t["type_int"] if link["is_internal"] else t["type_ext"]
                    })
                
                df_links = pd.DataFrame(formatted_links)
                st.dataframe(df_links, use_container_width=True)
                
                csv = df_links.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=t["download"],
                    data=csv,
                    file_name="qa_global_report.csv",
                    mime="text/csv",
                )
        else:
            st.error(f"{t['failed']} {result['error']}")
            save_to_history(target_url, "Failed", 0)

if __name__ == "__main__":
    main()
