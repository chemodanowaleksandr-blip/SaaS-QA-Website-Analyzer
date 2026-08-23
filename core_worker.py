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

# 2. Асинхронная проверка статуса конкретной ссылки
async def check_single_link(client: httpx.AsyncClient, link_data: dict):
    url = link_data["url"]
    try:
        # Отправляем быстрый HEAD-запрос вместо тяжелого GET
        response = await client.head(url, timeout=5.0, follow_redirects=True)
        
        # Если сайт вернул ошибку клиента или метода, страхуемся через GET-запрос
        if response.status_code == 404 or response.status_code == 405:
            response = await client.get(url, timeout=5.0, follow_redirects=True)
            
        link_data["status_code"] = response.status_code
        
        if response.status_code == 200:
            link_data["health"] = "🟢 OK"
        elif response.status_code >= 300 and response.status_code < 400:
            link_data["health"] = "🟡 Redirect"
        else:
            link_data["health"] = f"🔴 Broken ({response.status_code})"
    except Exception:
        link_data["status_code"] = 0
        link_data["health"] = "🔴 Broken (Timeout/Block)"
    return link_data

# Глобальный сборщик элементов и запуск конкурентного пула задач
async def analyze_website(url: str, is_premium: bool):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                return {"status": "Failed", "error": f"HTTP Error: {response.status_code}", "links": []}
                
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = str(response.url)
            
            raw_links = []
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
                raw_links.append({
                    "text": a_tag.text.strip() or "[No Text / Icon]",
                    "url": full_url,
                    "is_internal": is_internal,
                    "status_code": None,
                    "health": "⏳ Pending"
                })
            
            total_scanned = len(raw_links)
            if not is_premium:
                raw_links = raw_links[:10]
            
            # Запуск параллельного асинхронного пула задач
            tasks = [check_single_link(client, link) for link in raw_links]
            verified_links = await asyncio.gather(*tasks)
            
            return {
                "status": "Passed",
                "error": None,
                "links": verified_links,
                "total_count": total_scanned
            }
        except Exception as e:
            return {"status": "Failed", "error": str(e), "links": []}

# 3. Веб-интерфейс
def main():
    st.set_page_config(page_title="Enterprise QA Site Analyzer", page_icon="🔍", layout="wide")
    init_db()
    
    lang = st.sidebar.selectbox("🌐 Language / Язык", ["Русский", "English"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💎 Subscription / Подписка")
    promo_input = st.sidebar.text_input("Промокод / Promo Code", placeholder="STARTUP2026", type="password")
    is_premium = (promo_input.strip() == "STARTUP2026")
    
    if is_premium:
        st.sidebar.success("👑 PREMIUM ACTIVE / АКТИВЕН")
    else:
        st.sidebar.warning("🆓 FREE PLAN / БЕСПЛАТНЫЙ")
    
    t = {
        "Русский": {
            "title": "🔍 Глобальный SaaS QA Анализатор Сайтов",
            "subtitle": "Многопоточный асинхронный аудит доступности ссылок (HTTP Status Codes Validation) для СНГ и Европы.",
            "history": "📋 История проверок",
            "history_empty": "История пока пуста.",
            "placeholder": "Введите URL сайта для глубокого QA-анализа:",
            "button": "🚀 Запустить глубокий аудит доступности",
            "placeholder_input": "mysite.com",
            "warning": "Пожалуйста, укажите адрес сайта!",
            "info": "Инициализация асинхронного пула задач для: ",
            "spinner": "Движок пингует все найденные ссылки одновременно...",
            "success": "✅ ГЛУБОКИЙ АУДИТ ЗАВЕРШЕН — Обработано за {:.2f} сек.",
            "metric_status": "Статус главной страницы",
            "metric_links": "Всего ссылок на сайте",
            "table_title": "📊 Карта маршрутизации и валидация статусов (HTTP Health Check):",
            "col_text": "Текст элемента",
            "col_url": "Проверяемый URL",
            "col_type": "Тип ссылки",
            "col_code": "HTTP Код",
            "col_health": "Здоровье ссылки",
            "type_int": "Внутренняя",
            "type_ext": "Внешняя",
            "download": "📥 Скачать комплаенс-отчет (CSV)",
            "limit_notice": "⚠️ Лимит Free-плана: Проверено только первые 10 ссылок из {}. Введите промокод Premium для проверки всех элементов."
        },
        "English": {
            "title": "🔍 Global SaaS QA Website Analyzer",
            "subtitle": "Concurrent HTTP Status Codes Validation & Link Health Monitoring Engine.",
            "history": "📋 Scan History",
            "history_empty": "No scans yet.",
            "placeholder": "Enter website URL for deep QA-audit:",
            "placeholder_input": "example.com",
            "button": "🚀 Run Deep HTTP Health Audit",
            "warning": "Please enter a valid URL!",
            "info": "Initializing concurrent task pool for: ",
            "spinner": "Engine is pinging all extracted URLs simultaneously...",
            "success": "✅ DEEP AUDIT COMPLETE — Processed in {:.2f} seconds.",
            "metric_status": "Main Page Status",
            "metric_links": "Total Links Extracted",
            "table_title": "📊 Routing Map & HTTP Health Status Validation Table:",
            "col_text": "Element Text",
            "col_url": "Target URL",
            "col_type": "Link Type",
            "col_code": "HTTP Code",
            "col_health": "Link Health",
            "type_int": "Internal",
            "type_ext": "External",
            "download": "📥 Download Compliance Report (CSV)",
            "limit_notice": "⚠️ Free Plan Limit: Evaluated only first 10 links out of {}. Activate Premium to audit the entire infrastructure."
        }
    }[lang]

    st.title(t["title"])
    st.caption(t["subtitle"])
    
    st.sidebar.markdown("---")
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

    user_input = st.text_input(t["placeholder"], placeholder=t["placeholder_input"])
    
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
            result = asyncio.run(analyze_website(target_url, is_premium))
            end_time = time.time()
            
        if result["status"] == "Passed":
            st.success(t["success"].format(end_time - start_time))
            save_to_history(target_url, "Passed", len(result["links"]))
            
            col1, col2 = st.columns(2)
            col1.metric(t["metric_status"], "200 OK")
            col2.metric(t["metric_links"], result["total_count"])
            
            if result["links"]:
                st.subheader(t["table_title"])
                
                formatted_links = []
                for link in result["links"]:
                    formatted_links.append({
                        t["col_text"]: link["text"][:40],
                        t["col_url"]: link["url"],
                        t["col_type"]: t["type_int"] if link["is_internal"] else t["type_ext"],
                        t["col_code"]: int(link["status_code"]) if link["status_code"] else "Error",
