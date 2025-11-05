import time
import requests

import redis
from flask import Flask

app = Flask(__name__)
cache = redis.Redis(host='redis', port=6379)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

@app.route('/')
def hello():
    count = get_hit_count()
    return f'Hello from Docker! I have been seen {count} times.\n'

# Quick Notes:
# profiles, mutiple containers

@app.route('/weather', methods=["GET"])
def get_purdue_weather():
    latitude = "40.4237"
    longitude = "-86.9212"
    apiKey = "10e366371ff485eab0b32bb74beb9b6c"
    targetUrl = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={latitude}&lon={longitude}&appid={apiKey}&units=imperial"
    )
    res = requests.get(targetUrl)
    resJson = res.json()
    temp = resJson.get('main', {}).get('temp')
    return f"Current temperature in Purdue (in Fahrenheit): {temp}°F\n"