import io
import time
import httpx
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from reports import generate_excel_report

# 1. Функция сохранения истории
def save_to_history(url, status):
    if "history_dark" not in st.session_state:
        st.session_state["history_dark"] = []
    st.session_state["history_dark"].insert(0, {
        "URL": url,
        "Status": status,
        "Time": time.strftime("%Y-%m-%d %H:%M:%S")
    })

# 2. Стабильная проверка статуса конкретной ссылки
def check_single_link(client, link_data):
    url = link_data["url"]
    try:
        response = client.head(url, timeout=3.0, follow_redirects=True)
        if response.status_code in:
            response = client.get(url, timeout=3.0, follow_redirects=True)
        
        link_data["status_code"] = response.status_code
        
        if response.status_code == 200:
            link_data["health"] = "🟢 OK"
        elif 300 <= response.status_code < 400:
            link_data["health"] = "🟡 Redirect"
        else:
            link_data["health"] = f"🔴 Broken ({response.status_code})"
    except Exception:
        link_data["status_code"] = 0
        link_data["health"] = "🔴 Broken (Timeout/Block)"
        
    return link_data

# 3. Сборщик элементов страницы
def analyze_website(url, is_premium):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True, verify=False) as client:
            response = client.get(url)
            if response.status_code != 200:
                return {"status": "failed", "error": f"HTTP error {response.status_code}", "links": []}
                
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
                    "text": a_tag.text.strip() or "[No text / Icon]",
                    "url": full_url,
                    "is_internal": is_internal,
                    "status_code": None,
                    "health": "Pending"
                })
                
            total_scanned = len(raw_links)
            if not is_premium:
                raw_links = raw_links[:30]
                
            checked_links = []
            for link in raw_links:
                checked_links.append(check_single_link(client, link))
                
            return {
                "status": "passed",
                "links": checked_links,
                "total_count": total_scanned
            }
    except Exception as e:
        return {"status": "failed", "error": str(e), "links": []}

# 4. Веб-интерфейс
def main():
    st.set_page_config(page_title="Enterprise QA Site Analyzer", page_icon="🔍", layout="wide")

    if "history_dark" not in st.session_state:
        st.session_state["history_dark"] = []

    lang = st.sidebar.selectbox("🌐 Language / Язык", ["Русский", "English"])

    st.sidebar.markdown("---")
    st.sidebar.subheader("🪪 Subscription / Подписка")
    promo_input = st.sidebar.text_input("Промокод / Promo code", placeholder="STARTUP2026", type="password")
    is_premium = promo_input.strip() == "STARTUP2026"

    if is_premium:
        st.sidebar.success("✅ PREMIUM ACTIVE / АКТИВЕН")
    else:
        st.sidebar.warning("⚠️ FREE PLAN / БЕСПЛАТНЫЙ")

    t = {
        "Русский": {
            "title": "🔍 Глобальный Аудит QA Анализатор Сайтов",
            "subtitle": "Многопоточный аудит доступности ссылок (HTTP status codes validation) для СНГ и Европы.",
            "history": "История проверок",
            "history_empty": "История пока пуста.",
            "placeholder": "Введите URL сайта для глубокого QA-анализа:",
            "button": "🚀 Запустить глубокий аудит доступности",
            "placeholder_input": "mysite.com",
            "warning": "Пожалуйста, укажите адрес сайта!",
            "info": "Инициализация пула задач для: ",
            "spinner": "Движок проверяет работоспособность ссылок...",
            "success": "🔥 Глубокий аудит завершен - обработано за {:.2f} сек.",
            "metric_status": "Статус главной страницы",
            "metric_links": "Всего ссылок на сайте",
            "table_title": "📊 Карта маршрутизации и валидация статусов (HTTP Health Check):",
            "col_text": "Текст элемента",
            "col_url": "Проверяемый URL",
            "col_type": "Тип ссылки",
            "col_code": "HTTP Код",
            "col_health": "Здоровье ссылки",
            "download": "📥 Скачать комплаенс-отчет (Excel)",
            "limit_notice": "⚠️ Free план лимит: Проверено только первые 30 ссылок из {}. Введите промокод Premium для проверки всех элементов.",
            "type_int": "Внутренняя",
            "type_ext": "Внешняя",
            "failed": "Ошибка анализа"
        },
        "English": {
            "title": "🔍 Global Giant QA Website Analyzer",
            "subtitle": "HTTP status codes validation & Link health monitoring engine.",
            "history": "Scan History",
            "history_empty": "No scans yet.",
            "placeholder": "Enter website URL for deep qa-audit:",
            "placeholder_input": "example.com",
            "button": "🚀 Run Deep HTTP Health Audit",
            "warning": "Please enter a valid URL.",
            "info": "Initializing task pool for: ",
            "spinner": "Engine is pinging all extracted URLs...",
            "success": "🔥 DEEP AUDIT COMPLETE - Processed in {:.2f} seconds.",
            "metric_status": "Main Page Status",
            "metric_links": "Total Links Extracted",
            "table_title": "📊 Routing Map & HTTP Health Status Validation Table:",
            "col_text": "Element text",
            "col_url": "Target URL",
            "col_type": "Link Type",
            "col_code": "HTTP Code",
            "col_health": "Link Health",
            "download": "📥 Download compliance report (Excel)",
            "limit_notice": "⚠️ Free Plan Limit: Evaluated only first 30 links out of {}. Activate Premium to audit the entire infrastructure.",
            "type_int": "Internal",
            "type_ext": "External",
            "failed": "Analysis Failed"
        }
    }[lang]

    st.title(t["title"])
    st.caption(t["subtitle"])

    st.sidebar.markdown("---")
    st.sidebar.header(t["history"])

    if st.session_state["history_dark"]:
        df_history = pd.DataFrame(st.session_state["history_dark"])
        st.sidebar.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.sidebar.info(t["history_empty"])

    # Форма под Enter
    with st.form(key="qa_audit_form", clear_on_submit=False):
        user_input = st.text_input(t["placeholder"], placeholder=t["placeholder_input"])
        submit_button = st.form_submit_button(t["button"], type="primary")

    if submit_button:
        if not user_input:
            st.warning(t["warning"])
            return

        target_url = user_input.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        st.info(f"{t['info']} [{target_url}]({target_url})")

        with st.spinner(t["spinner"]):
            start_time = time.time()
            result = analyze_website(target_url, is_premium)
            end_time = time.time()

        if result["status"] == "passed":
            st.success(t["success"].format(end_time - start_time))
            save_to_history(target_url, "Passed")

            col1, col2 = st.columns(2)
            col1.metric(t["metric_status"], "200 OK")
            col2.metric(t["metric_links"], result["total_count"])

            if result["links"]:
                st.subheader(t["table_title"])

                formatted_links = []
                for link in result["links"]:
                    item = {
                        t["col_text"]: link["text"][:40],
                        t["col_url"]: link["url"],
                        t["col_type"]: t["type_int"] if link["is_internal"] else t["type_ext"],
                        t["col_code"]: int(link["status_code"]) if link["status_code"] else "Error",
                        t["col_health"]: link["health"]
                    }
                    formatted_links.append(item)

                df_links = pd.DataFrame(formatted_links)

                if not is_premium:
                    st.warning(t["limit_notice"].format(result["total_count"]))

                st.dataframe(df_links, use_container_width=True, hide_index=True)

                if is_premium:
                    excel_file = generate_excel_report(formatted_links)
                    st.download_button(
                        label=t["download"],
                        data=excel_file,
                        file_name="qa_deep_health_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.button(t["download"], disabled=True)
        else:
            st.error(f"{t['failed']} | {result['error']}")
            save_to_history(target_url, "Failed")
if __name__ == "__main__":
    main()

