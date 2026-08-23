import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def analyze_website(target_url: str) -> dict:
    print(f"🤖 Начинаем автоматический QA-аудит для: {target_url}...")
    report = {
        "url": target_url,
        "status_code": None,
        "load_time_sec": None,
        "broken_links": [],
        "total_links_checked": 0,
        "verdict": "Passed"
    }

    # 1. Проверяем доступность сайта и скорость ответа
    try:
        start_time = time.time()
        response = requests.get(target_url, timeout=10)
        end_time = time.time()
        
        report["status_code"] = response.status_code
        report["load_time_sec"] = round(end_time - start_time, 2)
        
        if response.status_code != 200:
            report["verdict"] = "Failed (Site is down or returned error)"
            return report
            
    except requests.exceptions.RequestException as e:
        report["verdict"] = f"Failed (Cannot connect to site: {e})"
        return report

    # 2. Собираем все внутренние ссылки на странице
    soup = BeautifulSoup(response.text, 'html.parser')
    links = set()
    domain = urlparse(target_url).netloc

    for tag in soup.find_all('a', href=True):
        href = tag['href']
        full_url = urljoin(target_url, href)
        
        if urlparse(full_url).netloc == domain:
            links.add(full_url)

    report["total_links_checked"] = len(links)
    print(f"🔎 Найдено {len(links)} внутренних ссылок для проверки...")

    # 3. Сканируем найденные ссылки на ошибки (4xx и 5xx)
    for link in list(links)[:10]:  # Ограничим до 10 для скорости
        try:
            link_resp = requests.head(link, timeout=5, allow_redirects=True)
            if link_resp.status_code >= 400:
                report["broken_links"].append({"url": link, "status": link_resp.status_code})
        except requests.exceptions.RequestException:
            report["broken_links"].append({"url": link, "status": "Connection Error"})

    if report["broken_links"]:
        report["verdict"] = "Warning (Broken links found)"

    return report


def generate_txt_report(data: dict) -> str:
    """Функция для генерации красивого файла отчета"""
    # Очищаем имя домена для названия файла (например, https://ya.ru -> ya_ru)
    parsed_url = urlparse(data["url"])
    domain_name = parsed_url.netloc.replace('.', '_')
    filename = f"report_{domain_name}.txt"
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Собираем текст отчета
    report_text = f"=========================================\n"
    report_text += f"       SaaS QA AUTOMATED REPORT          \n"
    report_text += f"=========================================\n"
    report_text += f"Дата проверки:       {current_time}\n"
    report_text += f"Тестируемый URL:     {data['url']}\n"
    report_text += f"Статус ответа:       {data['status_code']}\n"
    report_text += f"Время загрузки:      {data['load_time_sec']} сек\n"
    report_text += f"Проверено ссылок:    {data['total_links_checked']}\n"
    report_text += f"-----------------------------------------\n"
    report_text += f"ИТОГОВЫЙ ВЕРДИКТ:    {data['verdict']}\n"
    report_text += f"=========================================\n"
    
    if data["broken_links"]:
        report_text += "\nСПИСОК ОБНАРУЖЕННЫХ БИТЫХ ССЫЛОК:\n"
        for idx, broken in enumerate(data["broken_links"], 1):
            report_text += f"{idx}. [{broken['status']}] {broken['url']}\n"
    else:
        report_text += "\nЗамечаний нет. Все проверенные ссылки работают корректно.\n"
        
    # Записываем в файл
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_text)
        
    return filename


if __name__ == "__main__":
    test_site = "https://ya.ru" 
    result = analyze_website(test_site)
    
    # Генерируем файл
    created_file = generate_txt_report(result)
    
    print("\n📊 --- ОТЧЕТ О ТЕСТИРОВАНИИ --- 📊")
    print(f"Итоговый статус: {result['verdict']}")
    print(f"💾 Отчет успешно сохранен в файл: {created_file}")
