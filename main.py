import logging
import os
import requests
import telebot
from telebot import types
from aiogram.client import telegram
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import concurrent.futures


foreing_language = "Deutsh"
#foreing_language = "English"
foreign_language_pattern = "подгр.сб.нем.яз."


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

    @bot.message_handler(commands=['start'])
    def start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button = types.KeyboardButton("Get Schedule")
        markup.add(button)
        bot.send_message(message.chat.id, "Welcome! Press the button below to get the schedule.", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == "Get Schedule")
    def send_schedule(message):
        logging.info("Button pressed: Get Schedule")

        html_content = fetch_data(website_url)
        tbody_content = extract_tr_tags_content(html_content)
        current_week = 9  # TODO: change later to auto search current week
        lectures_content = extract_lecture_times(tbody_content, current_week)

        # Split the response into parts if it's too long
        max_message_length = 4096
        for i in range(0, len(lectures_content), max_message_length):
            part = lectures_content[i:i + max_message_length]
            bot.send_message(message.chat.id, part, parse_mode='Markdown')

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

    logging.info("Fetched html page")

    return response.text


def extract_tr_tags_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    if rows:
        answer = ''.join(str(row) for row in rows)
        return answer[372:99999999999]  # temporal solution
    return "No rows found"


def extract_lecture_times(html, current_week): #TODO rewrite this peace of shit ASAP ASAP ASAP ASAP
    var2 = True
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    answer = ""
    pattern = r'([01]?\d|2[0-3]):[0-5]\d-([01]?\d|2[0-3]):[0-5]\d'

    weekday = ""
    td_tags = []
    for row in rows:
        if row.find('td', class_='wday'):
            weekday = row.find('td', class_='wday').text.strip()
        else:
            row_soup = BeautifulSoup(str(row), 'html.parser')
            td_tags = row_soup.find_all('td')

        if len(td_tags) > 1:
            if weekday:
                answer += f"\n\n{weekday}\n\n"
                if weekday == "вторник":
                    answer = answer[:-10]
                    answer += "14: 35 - 15:55\nИностранный язык(Практические занятия)\nподгр.сб.нем.яз.\nБосак Алёна Анатольевна\n4 / 901\n\nвторник\n\n"
                weekday = ""

            if row.find_all('td')[0].text == "подгр.ДКН-1" and var2:
                answer = answer[:-54]
                var2  = False

            if row.find_all('td')[0].text == "подгр.сб.нем.яз.":
                answer = answer[:-1]
                for td in td_tags:
                    answer += f"*{td.text}*\n"
            week_info = td_tags[1].text.strip()
            if is_current_week(week_info, current_week):

                for td_tag in row.find_all('td'):
                    if re.match(foreign_language_pattern, td_tag.text):
                        answer += "f{td.text}\n"
                    match = re.search(pattern, td_tag.text)
                    if match:
                        for i, td in enumerate(td_tags):
                            if i != 1:
                                if re.match(pattern, td.text):
                                    answer += f"*{td.text}*\n"
                                elif re.search(r'\d+', td.text):
                                    answer += f"*{td.text}*\n"
                                else:
                                    answer += f"{td.text.replace(' ,  ',',\n')}\n"
                answer += "\n"

    return answer


def is_current_week(week_info, current_week):
    week_info = week_info.replace('(', '').replace(')', '').replace(' ', '')
    week_numbers = re.findall(r'\d+-\d+|\d+', week_info)

    for num in week_numbers:
        if '-' in num:
            start, end = map(int, num.split('-'))
            if start <= current_week <= end:
                return True
        elif int(num) == current_week:
            return True
    return False



def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting the bot...")

    telegram_bot_token, website_url = load_api_credentials()

    bot = setup_bot(telegram_bot_token, website_url)
    logging.info("Started the bot")

    bot.infinity_polling()


if __name__ == '__main__':
    main()