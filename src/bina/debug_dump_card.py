from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")

d = webdriver.Chrome(options=opts)
d.get("https://bina.az/baki/alqi-satqi")
time.sleep(4)

cards = d.find_elements(By.CSS_SELECTOR, "div[data-cy='item-card']")
print("CARDS =", len(cards))

if cards:
    html = cards[0].get_attribute("innerHTML")
    print("===== CARD HTML START =====")
    print(html)
    print("===== CARD HTML END =====")
else:
    print("NO CARDS FOUND")

d.quit()
