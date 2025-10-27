import requests
from bs4 import BeautifulSoup
from telegram import Bot
import schedule
import time
import json
import os
import asyncio
import logging

# Настройка логирования (для Amvera)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Настройки
TOKEN = "8236935826:AAHj_sOj_KxwRP_Ap6w7L54TDMX3hpW8qhU"
CHAT_ID = "1667167956"  # Твой Chat ID
URL = "https://cars.av.by/filter?price_usd[min]=2850&price_usd[max]=4200&transmission_type[0]=2&engine_type[0]=1&place_region[0]=1005&seller_type[0]=1&mileage_km[max]=400000&sort=4"
CHECK_INTERVAL = 30 * 60  # 30 минут в секундах
SEEN_ADS_FILE = "seen_ads.json"  # Файл для хранения ID просмотренных объявлений

# Инициализация бота
bot = Bot(token=TOKEN)

# Заголовки для имитации браузера
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Загрузка ранее просмотренных объявлений
def load_seen_ads():
    if os.path.exists(SEEN_ADS_FILE):
        with open(SEEN_ADS_FILE, "r") as file:
            return set(json.load(file))
    return set()

# Сохранение просмотренных объявлений
def save_seen_ads(seen_ads):
    with open(SEEN_ADS_FILE, "w") as file:
        json.dump(list(seen_ads), file)

# Асинхронная функция для отправки сообщений
async def send_message(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f"Отправлено в Telegram: {text}")
    except Exception as e:
        logger.error(f"Ошибка при отправке в Telegram: {e}")

# Парсинг страницы
def check_new_ads():
    try:
        seen_ads = load_seen_ads()
        response = requests.get(URL, headers=headers)
        response.raise_for_status()  # Проверка на ошибки HTTP
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Находим все объявления на странице
        ads = soup.find_all("div", class_="listing-item")
        
        new_ads = []
        for ad in ads:
            # Извлекаем ссылку на объявление
            ad_link = ad.find("a", class_="listing-item__link")
            if ad_link:
                ad_url = "https://cars.av.by" + ad_link["href"]
                ad_id = ad_url.split("/")[-1]  # ID обычно в конце URL
                if ad_id not in seen_ads:
                    new_ads.append(ad_url)
                    seen_ads.add(ad_id)
        
        # Сохраняем обновлённый список просмотренных объявлений
        save_seen_ads(seen_ads)
        
        # Запускаем асинхронную отправку сообщений
        loop = asyncio.new_event_loop()  # Новый loop для облака
        asyncio.set_event_loop(loop)
        if new_ads:
            for ad_url in new_ads:
                loop.run_until_complete(send_message(ad_url))
        else:
            loop.run_until_complete(send_message("Новых объявлений нет"))
        loop.close()

        logger.info("Проверка завершена")

    except Exception as e:
        error_message = f"Ошибка при проверке объявлений: {e}"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_message(error_message))
        loop.close()
        logger.error(error_message)

# Планировщик задач
def main():
    schedule.every(CHECK_INTERVAL).seconds.do(check_new_ads)
    logger.info("Бот запущен в облаке, проверка каждые 30 минут...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту, но задачи выполняются по расписанию

if __name__ == "__main__":
    main()