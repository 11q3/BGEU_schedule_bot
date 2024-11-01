import os
import re
import telebot
import logging
import requests
from telebot import types
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from collections import defaultdict

week = 9 # TODO: change later to auto search current week, temporal solution for now

def load_api_credentials():
    load_dotenv()
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    website_url = os.environ.get("WEBSITE_URL")
    subgroup = os.environ.get("SUBGROUP")
    sub_subgroup = os.environ.get("SUB_SUBGROUP")

    if not telegram_bot_token:
        logging.error("TELEGRAM_BOT_TOKEN is not set in environment variables")
        raise SystemExit(1)

    if not website_url:
        logging.error("WEBSITE_URL is not set in environment variables")
        raise SystemExit(1)

    if not subgroup:
        logging.error("SUBGROUP is not set in environment variables")
        raise SystemExit(1)

    if not sub_subgroup:
        logging.error("SUB_SUBGROUP is not set in environment variables")
        raise SystemExit(1)

    return telegram_bot_token, website_url, subgroup, sub_subgroup


def create_telegram_bot(telegram_bot_token):
    try:
        bot = telebot.TeleBot(telegram_bot_token)
        return bot
    except Exception as e:
        logging.error(f"Error creating Telegram bot instance: {e}")
        raise SystemExit(1)



def setup_bot(telegram_bot_token, website_url, subgroup, sub_subgroup):
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

        html_doc = fetch_data(website_url)
        schedule_table = parse_html(html_doc)
        lectures_content = "No schedule found."

        if schedule_table:
            lecture_info = extract_lecture_info(schedule_table, week, subgroup, sub_subgroup)
            lectures_content = display_lecture_info(lecture_info)

        max_message_length = 4096
        for i in range(0, len(lectures_content), max_message_length):
            part = lectures_content[i:i + max_message_length]
            bot.send_message(message.chat.id, part, parse_mode='Markdown')

        logging.info("Finished answering a message")

    return bot


def display_lecture_info(lecture_info):
    output = []
    if lecture_info:
        for day, lectures in lecture_info.items():
            output.append(f"{day}:")
            for lecture in lectures:
                output.append(f"  Time: {lecture['Time']}")
                output.append(f"  Subject: {lecture['Subject']}")
                output.append(f"  Teacher: {lecture['Teacher']}")
                output.append(f"  Classroom: {lecture['Classroom']}")
                output.append("")
    else:
        output.append("No lectures found for the current week.")
    return "\n".join(output)

def extract_lecture_info(schedule_table, current_week, subgroup, sub_subgroup):
    lecture_info = defaultdict(list)
    current_day = None

    for row in schedule_table.find_all('tr'):
        cells = row.find_all('td')

        if len(cells) == 1 and 'colspan' in cells[0].attrs:
            current_day = cells[0].text.strip()
            continue

        if len(cells) >= 3 and 'Иностранный язык' in cells[2].text:
            lectures = process_language_rows(row, current_week, subgroup, sub_subgroup)
            for lecture in lectures:
                if lecture not in lecture_info[current_day]:
                    lecture_info[current_day].append(lecture)
        elif len(cells) == 4:
            lecture = process_regular_rows(cells, current_week)
            if lecture and lecture not in lecture_info[current_day]:
                lecture_info[current_day].append(lecture)

    return lecture_info

def process_language_rows(row, current_week, subgroup, sub_subgroup):
    lecture_info = []
    time = row.find_all('td')[0].text.strip()
    week_info = row.find_all('td')[1].text.strip()

    if not get_week_match(week_info, current_week):
        return lecture_info

    subject = row.find_all('td')[2].text.strip()
    for group_row in row.find_next_siblings('tr'):
        group_cells = group_row.find_all('td')
        if len(group_cells) == 3:
            group = group_cells[0].text.strip()
            teacher = group_cells[1].text.strip()
            classroom = group_cells[2].text.strip()

            if subgroup in group or sub_subgroup in group:
                lecture = {
                    'Time': time,
                    'Subject': f"{subject} ({group})",
                    'Teacher': teacher,
                    'Classroom': classroom
                }
                if lecture not in lecture_info:
                    lecture_info.append(lecture)
        else:
            break

    return lecture_info

def process_regular_rows(cells, current_week):
    time = cells[0].text.strip()
    week_info = cells[1].text.strip()

    if not get_week_match(week_info, current_week):
        return None

    subject_and_teacher = cells[2].text.strip()
    classroom = cells[3].text.strip()

    if ',' in subject_and_teacher:
        subject, teacher = subject_and_teacher.rsplit(',', 1)
        subject = subject.strip()
        teacher = teacher.strip()
    else:
        subject = subject_and_teacher
        teacher = ''

    return {
        'Time': time,
        'Subject': subject,
        'Teacher': teacher,
        'Classroom': classroom
    }


def get_week_match(week_info, current_week):
    week_match = re.findall(r'\d+(?:-\d+)?', week_info)
    for week in week_match:
        if '-' in week:
            start, end = map(int, week.split('-'))
            if start <= current_week <= end:
                return True
        else:
            if int(week) == current_week:
                return True
    return False

def fetch_data(website_url): # DONE
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
        'week': week,
        '__act': '__id.25.main.inpFldsA.GetSchedule__sp.7.results__fp.4.main'
    }

    response = requests.post(website_url, headers=headers, data=data)

    logging.info("Fetched html page")

    return response.text

def parse_html(html_doc):
    soup = BeautifulSoup(html_doc, 'html.parser')
    return soup.find('table', {'id': 'sched'})


def extract_tr_tags_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    if rows:
        answer = ''.join(str(row) for row in rows)
        return answer[372:99999999999]  # temporal solution
    return "No rows found"


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

    telegram_bot_token, website_url, subgroup, sub_subgroup = load_api_credentials()

    bot = setup_bot(telegram_bot_token, website_url, subgroup, sub_subgroup)
    logging.info("Started the bot")

    bot.infinity_polling()


if __name__ == '__main__':
    main()