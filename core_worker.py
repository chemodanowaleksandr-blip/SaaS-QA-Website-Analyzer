import os
import time
import httpx
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor
from reports import generate_excel_report

# ИМПОРТИРУЕМ НАШИ МОДУЛИ
from database import save_to_db_history, get_db_history
from auth import render_auth_section
from config import get_localization

def check_single_link(client, link_data):
    url = link_data["url"]
    try:
        response = client.head(url, timeout=5.0, follow_redirects=True)
        if response.status_code >= 400:
            response = client.get(url, timeout=5.0, follow_redirects=True)
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

def analyze_website(url, is_premium):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
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
                    "text": a_tag.get_text().strip() or "[No text / icon]",
                    "url": full_url,
                    "is_internal": is_internal,
                    "status_code": None,
                    "health": "Pending"
                })
            
            total_scanned = len(raw_links)
            if not is_premium:
                raw_links = raw_links[:50]
                
            with ThreadPoolExecutor(max_workers=20) as executor:
                checked_links = list(executor.map(lambda l: check_single_link(client, l), raw_links))
                
            return {"status": "passed", "links": checked_links, "total_count": total_scanned}
    except Exception as e:
        return {"status": "failed", "error": str(e), "links": []}

def trigger_audit():
    st.session_state["run_processing"] = True

def main():
    st.set_page_config(page_title="Enterprise QA Site Analyzer", page_icon="🔍", layout="wide")
    
    if "run_processing" not in st.session_state:
        st.session_state["run_processing"] = False
    if "selected_url" not in st.session_state:
        st.session_state["selected_url"] = ""
        
    lang = st.sidebar.selectbox("🌐 Language / Язык", ["Русский", "English"])
    st.sidebar.markdown("---")
    
    # Сначала генерируем базовый языковой пакет
    t_init = get_localization(lang, "Guest")
    
    # Передаем его в авторизацию
    user_session = render_auth_section(t_init)
    if not user_session:
        st.info(t_init["welcome_info"])
        return
        
    current_user = user_session["username"]
    is_premium = user_session["plan"] == "premium"
    
    # Пересобираем локализацию уже с реальным именем вошедшего пользователя
    t = get_localization(lang, current_user)
    
    st.title(t["title"])
    st.caption(t["subtitle"])
    st.sidebar.markdown("---")
    st.sidebar.subheader(t["history"])
    
    db_data = get_db_history(current_user)
    if db_data:
        df_history = pd.DataFrame(db_data)
        selected = st.sidebar.dataframe(df_history, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single_row")
        if selected and selected["selection"]["rows"]:
            row_idx = selected["selection"]["rows"]
            st.session_state["selected_url"] = df_history.iloc[row_idx]["URL"]
            st.session_state["run_processing"] = True
    else:
        st.sidebar.info(t["history_empty"])
        
    default_url = st.session_state["selected_url"] if st.session_state["selected_url"] else ""
    user_input = st.text_input("URL сайта:", value=default_url, placeholder=t["placeholder_input"], key="site_url_input", on_change=trigger_audit)
    
    if st.button(t["button"], type="primary") or st.session_state["run_processing"]:
        st.session_state["run_processing"] = False
        st.session_state["selected_url"] = ""
        
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
            save_to_db_history(current_user, target_url, "Passed")
            
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
                        t["col_health"]: link["health"]
                    })
                df_links = pd.DataFrame(formatted_links)
                if not is_premium and result["total_count"] > 50:
                    st.warning(t["limit_notice"].format(result["total_count"]))
                st.dataframe(df_links, use_container_width=True, hide_index=True)
                
                if is_premium:
                    excel_file = generate_excel_report(formatted_links)
                    st.download_button(label=t["download"], data=excel_file, file_name="qa_deep_health_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.button(t["download"], disabled=True)
            st.rerun()
        else:
            st.error(f"{t['failed']}: {result['error']}")
            save_to_db_history(current_user, target_url, "Failed")
            st.rerun()

if __name__ == "__main__":
    main()
