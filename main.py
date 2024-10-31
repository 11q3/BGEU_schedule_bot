import logging
import os
import requests
import telebot
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re


def load_api_credentials():
    load_dotenv()
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    website_url = os.environ.get("WEBSITE_URL")

    if not telegram_bot_token:
        logging.error("TELEGRAM_BOT_TOKEN is not set in environment variables")
        raise SystemExit(1)

    if not website_url:
        logging.error("WEBSITE_URL is not set in environment variables")
        raise SystemExit(1)

    return telegram_bot_token, website_url


def create_telegram_bot(telegram_bot_token):
    try:
        bot = telebot.TeleBot(telegram_bot_token)
        return bot
    except Exception as e:
        logging.error(f"Error creating Telegram bot instance: {e}")
        raise SystemExit(1)


def setup_bot(telegram_bot_token, website_url):
    bot = create_telegram_bot(telegram_bot_token)

    @bot.message_handler(func=lambda message: True)
    def echo(message):
        logging.info("Received a message")

        html_content = fetch_data(website_url)
        tbody_content = extract_tbody_content(html_content)
        lectures_content = extract_lecture_times(tbody_content)

        # Split the response into parts if it's too long
        max_message_length = 4096
        for i in range(0, len(lectures_content), max_message_length):
            part = lectures_content[i:i + max_message_length]
            bot.reply_to(message, part)

        logging.info("Finished answering a message")

    return bot


def fetch_data(website_url):
    current_week = 9  # TODO: change later to auto search current week

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'faculty': '11',
        'form': '10',
        'course': '1',
        'group': '9499',
        'tname': '',
        'period': '3',
        'week': current_week,
        '__act': '__id.25.main.inpFldsA.GetSchedule__sp.7.results__fp.4.main'
    }

    response = requests.post(website_url, headers=headers, data=data)
    response.encoding = 'windows-1251'

    logging.info("Fetched html page")

    return response.text


def extract_tbody_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    if rows:
        answer = ''.join(str(row) for row in rows)
        return answer[372:99999999999]  # temporal solution
    return "No rows found"


def extract_lecture_times(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    answer = ""
    pattern = r'([01]?\d|2[0-3]):[0-5]\d-([01]?\d|2[0-3]):[0-5]\d'

    for row in rows:
        row_soup = BeautifulSoup(str(row), 'html.parser')
        td_tags = row_soup.find_all('td')

        for td_tag in td_tags:
            var = td_tag.text
            match = re.search(pattern, var)
            if match:
                answer += " ".join(td.text for td in td_tags) + " \n"
        answer += "\n\n"

    return answer


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting the bot...")

    telegram_bot_token, website_url = load_api_credentials()

    bot = setup_bot(telegram_bot_token, website_url)
    logging.info("Started the bot")

    bot.infinity_polling()


if __name__ == '__main__':
    main()
