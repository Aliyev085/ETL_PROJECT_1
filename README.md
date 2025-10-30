# 🧾 BINA.AZ ETL SYSTEM — Automated Real Estate Data Pipeline

**Author:** Mahammad Aliyev  
**Stack:** Python · Selenium · RabbitMQ · PostgreSQL · Docker · Cron · Systemd  
**Deployment:** Remote Linux Server (VS Code SSH) with Dockerized Services  

---

## 🧠 Overview
The **Bina.az ETL System** is a fully automated, two-phase data pipeline designed to continuously scrape, enrich, and store real estate listings from [bina.az](https://bina.az).  
It integrates **Python**, **RabbitMQ**, and **PostgreSQL** into a distributed, fault-tolerant ETL architecture that operates autonomously using **cron jobs** and **systemd** services.  
Built to production standards — modular, scalable, and self-healing.

---

## 🏗️ Architecture
```
                 ┌───────────────────────────────┐
                 │     Scraper 1 (main.py)       │
                 │  Collects & inserts listings  │
                 └─────────────┬─────────────────┘
                               │
                               ▼
                         RabbitMQ Queue
                               │
                               ▼
                 ┌───────────────────────────────┐
                 │  Scraper 2 (scraper_each_item)│
                 │  Enriches listings in detail  │
                 └─────────────┬─────────────────┘
                               │
                               ▼
                        PostgreSQL Database
                               │
                               ▼
                    Continuous, Automated ETL
```

---

## ⚙️ System Components

### 🐍 1️⃣ Scraper 1 — main.py
- Entry point for the ETL pipeline.  
- Two modes:  
  - `--initial` → full scrape (first 100 listings)  
  - `--incremental` → periodic update (every 16 minutes)  
- Extracts listing metadata:  
  - ID, title, price, area, rooms, location, owner type.  
- Inserts new records into PostgreSQL (`bina_apartments`) and publishes each listing to RabbitMQ queue `listing_queue`.  

**Example Output:**
```
[x] Published listing_id=5619908 to queue listing_queue
[initial] inserted new rows: 100
```

---

### 🕵️‍♀️ 2️⃣ Scraper 2 — scraper_each_item.py
- Runs as a persistent **systemd service**.  
- Listens to RabbitMQ for new listings.  
- Uses **Selenium (headless Chrome / undetected-chromedriver)** to open each listing page.  
- Extracts:  
  - Description  
  - Owner name  
  - Contact number (AJAX fetch)  
  - View count  
  - Construction status  
- Updates existing rows in PostgreSQL with enriched data.  

**Example Output:**
```
[CALLBACK] Received message: {'listing_id': 5619908, 'url': 'https://bina.az/items/5619908'}
[SCRAPE] ID=5619908, Owner=Fikrət, Phone=+994 502099104, Views=167, Constructed=False
[DB] Updated listing_id=5619908 (1 rows)
[SCRAPE] ✅ Listing 5619908 updated successfully
```

---

### 🐇 3️⃣ RabbitMQ — Message Queue
- Acts as the **communication bridge** between Scraper 1 and Scraper 2.  
- Enables asynchronous processing and fault tolerance.  
- Runs in Docker, accessible on:  
  - **5672** → Broker port  
  - **15672** → Management UI  

**Check queue status:**
```
sudo docker exec -it rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

---

### 🗄️ 4️⃣ PostgreSQL Database
- Containerized PostgreSQL 16 (`etl_postgres`).  
- Central storage for all listings.  
- Table: `bina_apartments`

**Columns:**
```
listing_id, title, price, rooms, area, location,
description, contact_number, posted_by, view_count,
is_constructed, is_scraped
```

**Example Check:**
```
SELECT COUNT(*) FROM bina_apartments WHERE is_scraped = true;
```

---

### ⚙️ 5️⃣ Automation — Cron + Systemd

#### ⏰ Cron (Incremental ETL)
Runs Scraper 1 (`main.py --incremental`) every 16 minutes:
```
*/16 * * * * flock -n /tmp/bina_each_item.lock -c \
"cd /opt/Etl_server_project_1 && export $(grep -v '^#' .env | xargs) && \
export PYTHONPATH=/opt/Etl_server_project_1/src && \
/opt/Etl_server_project_1/etl/venv/bin/python -m bina.scraper_each_item >> \
/opt/Etl_server_project_1/logs/scraper_each_item.log 2>&1"
```

#### 🧩 Systemd Service (Continuous Detail Enrichment)
Keeps Scraper 2 always running and auto-restarts on crash:
```
sudo systemctl status bina_scraper_each_item.service
```

---

### 🧰 6️⃣ Environment Configuration (.env)
Stores all credentials and runtime parameters.
```
# --- Database ---
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=etlserver_db
DB_USER=Aliyev_user
DB_PASSWORD=EtlpostgresBlack1002025Xyz

# --- RabbitMQ ---
RABBIT_HOST=127.0.0.1
RABBIT_QUEUE=listing_queue

# --- Scraper Settings ---
BINA_BASE_URL=https://bina.az/baki/menziller
BINA_HEADLESS=1
BINA_MAX_LISTINGS_INITIAL=100
BINA_MAX_LISTINGS_INCREMENTAL=180
```

---

## 🐳 Dockerized Infrastructure

### docker-compose.yml
Runs:
- PostgreSQL 16  
- pgAdmin (port 5050)

### docker-compose.rabbitmq.yml
Runs:
- RabbitMQ with management UI  

**Launch all containers:**
```
docker-compose up -d
docker-compose -f docker-compose.rabbitmq.yml up -d
```

---

## 🧩 ETL Flow Summary
| Step | Component | Description |
|------|------------|-------------|
| 1️⃣ | main.py --initial | Scrapes and publishes listings |
| 2️⃣ | RabbitMQ | Passes listing IDs and URLs |
| 3️⃣ | scraper_each_item.py | Enriches listings with full details |
| 4️⃣ | PostgreSQL | Stores structured + enriched data |
| 5️⃣ | Cron + Systemd | Automate, schedule, and monitor |

---

## 🧱 Tech Stack
| Layer | Technology |
|-------|-------------|
| Language | Python 3.11 |
| Web Automation | Selenium / undetected-chromedriver |
| Messaging | RabbitMQ |
| Database | PostgreSQL 16 |
| Orchestration | Docker + Docker Compose |
| Automation | Cron + Systemd |
| Configuration | dotenv (.env) |

---

## 🚀 Deployment Guide
```
# 1. Start RabbitMQ
docker-compose -f docker-compose.rabbitmq.yml up -d

# 2. Start PostgreSQL + pgAdmin
docker-compose up -d

# 3. Run initial ETL
python3 src/main.py --initial

# 4. Enable continuous enrichment
sudo systemctl start bina_scraper_each_item.service
```

---

## 🧪 Testing & Tools
- `send_test_each_item.py` → manually publish a test message to queue  
- `receive_test.py` → verify queue connectivity  
- `test_db.py`, `test_rabbit.py` → integration tests  
- `run_scraper_each_item.sh` → quick systemd/cron runner  

---

## 📊 Logging & Monitoring
All logs are stored under:
```
/opt/Etl_server_project_1/logs/
 ├─ main_scraper.log
 ├─ scraper_each_item.log
 ├─ cron_bina_etl.log
 └─ bina_etl.log
```
Inspect logs live:
```
tail -f /opt/Etl_server_project_1/logs/scraper_each_item.log
```

---

## 🧾 Result
✅ Fully automated, distributed ETL pipeline  
✅ Decoupled architecture via message queue  
✅ Production-ready with persistent Dockerized storage  
✅ Resilient automation (cron + systemd)  
✅ Dynamic scraping with headless browser  
✅ PostgreSQL stays always up-to-date with real estate data  

---

## 👨‍💻 About the Author
**Mahammad Aliyev**  
_Data Engineer 
> Designed and implemented a production-grade, self-healing ETL system integrating  
> web automation, queue-based messaging, and containerized persistence —  
> delivering continuous, reliable real estate data collection at scale.

---

## 🏁 Final Note
This system represents a **real-world, enterprise-grade ETL pipeline** built from scratch using open-source technologies — scalable, observable, and aligned with modern data engineering principles.
