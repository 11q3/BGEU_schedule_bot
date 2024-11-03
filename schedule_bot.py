import os
import re
import time

import telebot
import logging
from collections import defaultdict
from telebot import types
from bs4 import BeautifulSoup
import requests

# Constants
MAX_RETRIES = 7  # Maximum number of retries for fetching schedule
TIMEOUT_SECONDS = 5  # Timeout duration for fetching the HTML page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def fetch_data(website_url, week):
    logging.info("Fetching data from website")
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

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"Fetch attempt {attempt}")
            response = requests.post(website_url, headers=headers, data=data, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            logging.info("Successfully fetched HTML page")
            return response.text
        except requests.exceptions.Timeout:
            logging.warning(f"Attempt {attempt}: Fetch timed out after {TIMEOUT_SECONDS} seconds")
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt}: Failed to fetch schedule - {e}")

        if attempt == MAX_RETRIES:
            logging.error("Max retries reached. Stopping the bot.")
            raise RuntimeError("Failed to fetch data after maximum retries.")


def parse_html(html_doc):
    logging.info("Parsing HTML document")
    soup = BeautifulSoup(html_doc, 'html.parser')
    table = soup.find('table', {'id': 'sched'})
    if table:
        logging.info("Successfully parsed HTML table")
    else:
        logging.warning("Schedule table not found in HTML document")
    return table


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


def extract_lecture_info(schedule_table, current_week, subgroup, sub_subgroup):
    logging.info("Extracting lecture information from schedule table")
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

    logging.info("Completed lecture extraction")
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


class ScheduleBot:
    def __init__(self, telegram_bot_token, website_url, subgroup, sub_subgroup):
        self.bot = telebot.TeleBot(telegram_bot_token)
        self.website_url = website_url
        self.subgroup = subgroup
        self.sub_subgroup = sub_subgroup
        self.cached_schedule_table = None
        self.week = 10  # TODO: Implement auto week detection

    def setup_bot(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.show_main_menu(message.chat.id)

        def show_main_menu(chat_id):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button_day = types.KeyboardButton("Get Schedule for Day")
            button_week = types.KeyboardButton("Get Schedule for Week")
            markup.add(button_day, button_week)
            self.bot.send_message(
                chat_id, "Welcome! Press a button below to get the schedule.", reply_markup=markup
            )

        @self.bot.message_handler(func=lambda message: message.text == "Get Schedule for Day")
        def select_day(message):
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]
            buttons = [types.KeyboardButton(day) for day in days]
            markup.add(*buttons)
            markup.add(types.KeyboardButton("Back"))
            self.bot.send_message(message.chat.id, "Please select a day to get the schedule.", reply_markup=markup)

        @self.bot.message_handler(
            func=lambda message: message.text in ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]
        )
        def send_schedule_for_day(message):
            logging.info(
                f"User {message.from_user.username} (ID: {message.from_user.id}) requested schedule for {message.text}"
            )

            lectures_content = "No schedule found."
            if self.cached_schedule_table:
                lecture_info = extract_lecture_info(
                    self.cached_schedule_table, self.week, self.subgroup, self.sub_subgroup
                )
                day_schedule = lecture_info.get(message.text)
                if day_schedule:
                    lectures_content = display_lecture_info({message.text: day_schedule})

            max_message_length = 4096
            for i in range(0, len(lectures_content), max_message_length):
                part = lectures_content[i:i + max_message_length]
                self.bot.send_message(message.chat.id, part, parse_mode='Markdown')

            logging.info(f"Completed schedule response to user {message.from_user.username} (ID: {message.from_user.id})")

        @self.bot.message_handler(func=lambda message: message.text == "Get Schedule for Week")
        def send_schedule_for_week(message):
            logging.info(
                f"User {message.from_user.username} (ID: {message.from_user.id}) requested schedule for the whole week"
            )

            lectures_content = "No schedule found."
            if self.cached_schedule_table:
                lecture_info = extract_lecture_info(
                    self.cached_schedule_table, self.week, self.subgroup, self.sub_subgroup
                )
                if lecture_info:
                    lectures_content = display_lecture_info(lecture_info)

            max_message_length = 4096
            for i in range(0, len(lectures_content), max_message_length):
                part = lectures_content[i:i + max_message_length]
                self.bot.send_message(message.chat.id, part, parse_mode='Markdown')

            logging.info(f"Completed weekly schedule response to user {message.from_user.username} (ID: {message.from_user.id})")

        @self.bot.message_handler(func=lambda message: message.text == "Back")
        def back_to_main_menu(message):
            show_main_menu(message.chat.id)

    def run(self):
        start_time = time.time()
        logging.info("Bot is starting up")

        html_doc = fetch_data(self.website_url, self.week)
        self.cached_schedule_table = parse_html(html_doc)  # Fetch and cache the schedule once at startup

        self.setup_bot()

        end_time = time.time()  # Log end time
        logging.info(f"Bot setup complete. Initialization time: {end_time - start_time:.2f} seconds")

        self.bot.infinity_polling()