import logging
from dotenv import load_dotenv
import os
from schedule_bot import ScheduleBot

def load_api_credentials():
    logging.info("Starting to load API credentials")

    load_dotenv()

    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    website_url = os.environ.get("WEBSITE_URL")
    subgroup = os.environ.get("SUBGROUP")
    sub_subgroup = os.environ.get("SUB_SUBGROUP")

    if not telegram_bot_token or not website_url or not subgroup or not sub_subgroup:
        logging.error("Some environment variables are not set.")
        raise ValueError("Missing required environment variables.")

    logging.info("Successfully loaded API credentials")

    return telegram_bot_token, website_url, subgroup, sub_subgroup

def main():
    try:
        telegram_bot_token, website_url, subgroup, sub_subgroup = load_api_credentials()

        schedule_bot = ScheduleBot(telegram_bot_token, website_url, subgroup, sub_subgroup)

        schedule_bot.run()
    except (ValueError, RuntimeError) as e:
        logging.error(f"Bot failed to start: {e}")

if __name__ == '__main__':
    main()
