from pollevbot import PollBot
import os
import dotenv

dotenv.load_dotenv()

user = os.getenv('EMAIL')
password = os.getenv('PASSWORD')
host = os.getenv('HOST')

with PollBot(user, password, host, login_type='pollev', lifetime=4800) as bot:
    bot.run()