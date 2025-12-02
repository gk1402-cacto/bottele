import os
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
RENDER_URL = os.environ["RENDER_URL"]

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
data = {"url": f"{RENDER_URL}/webhook"}

resp = requests.post(url, json=data)
print(resp.text)
