FROM python:3
MAINTAINER kuilin@gmail.com

COPY . /opt/egs_guess_bot
WORKDIR /opt/egs_guess_bot
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd srv
USER srv

CMD python3 -u bot.py
