FROM python:3
MAINTAINER kuilin@gmail.com

RUN mkdir -p /opt/egs_guess_bot
COPY requirements.txt /opt/egs_guess_bot
WORKDIR /opt/egs_guess_bot
RUN pip install --no-cache-dir -r requirements.txt

COPY . /opt/egs_guess_bot

RUN useradd srv
USER srv

CMD python3 -u bot.py
