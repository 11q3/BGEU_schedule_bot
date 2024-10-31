import logging
import os
import time
import requests
import telebot
from aiogram import Bot, Dispatcher, types
from aiogram import Router
from dotenv import load_dotenv
from bs4 import BeautifulSoup

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
        print(1)
        strr = fetch_data(website_url)
        print(strr)
        bot.reply_to(message, "1")

    return bot

def get_current_week():
    pass

def fetch_data(website_url):
    current_week = 9 #TODO change later to auto search current week

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
    return response.text

def main():
    logging.info("Starting the bot...")

    telegram_bot_token, website_url = load_api_credentials()

    bot = setup_bot(telegram_bot_token, website_url)

    bot.infinity_polling()

if __name__ == '__main__':
    main()
