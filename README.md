# SaaS QA Automated Website Analyzer (MVP)

A lightweight, automated QA tool written in Python to perform quick website audits, analyze performance, and detect broken links (4xx/5xx errors).

## Features
- **Availability Check:** Instantly measures HTTP status codes and tracks server connection drops.
- **Performance Metric:** Captures page load time in seconds.
- **Link Crawler:** Automatically parses the HTML, extracts internal links, and verifies their integrity via automated HEAD requests.
- **Automated Reporting:** Generates clean, production-ready `.txt` reports for end-users.

## Architecture
This project serves as the core scanning worker for a scalable No-Code/Low-Code SaaS platform architecture.

## Installation & Quick Start

1. Clone the repository:
```bash
git clone https://github.com
```

2. Install dependencies:
```bash
pip install requests beautifulsoup4
```

3. Run the audit:
```bash
python core_worker.py
```

## Tech Stack
- **Language:** Python 3.10+
- **Libraries:** Requests, BeautifulSoup4, Urllib, Time
