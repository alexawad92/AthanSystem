import logging
import os
import random
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from flask import Flask, jsonify, render_template


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, "athan.log")

LAT = 35.947789
LON = -84.174276

CITY = "Knoxville"
STATE = "Tennessee"
COUNTRY = "USA"

METHOD = 2
TIMEZONE = ZoneInfo("America/New_York")

PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

ATHAN_FILES = [
    os.path.join(BASE_DIR, "assets", "Athan1.wav"),
    os.path.join(BASE_DIR, "assets", "Athan2.wav"),
    os.path.join(BASE_DIR, "assets", "Athan3.wav"),
]

FAJR_ATHAN_FILE = os.path.join(BASE_DIR, "assets", "Fajr.wav")

# Your current audio device
AUDIO_DEVICE = "plughw:1,0"

# Delay before Flask starts
START_DELAY = 10

# Weather cache duration
WEATHER_CACHE_SECONDS = 600


# ============================================================
# TEST MODE
# ============================================================
#
# TEMPORARY TESTING ONLY
#
# When True:
#
#   App starts
#       ↓
#   30 seconds
#       ↓
#   Simulated prayer
#       ↓
#   Athan plays
#
# Set to False when finished testing.
#

TEST_MODE = False

TEST_PRAYER_DELAY = 30

# We will use a normal Athan for the test.
# Change to "Fajr" if you specifically want Fajr.wav.
TEST_PRAYER_NAME = "Maghrib"

test_start_time = None
test_triggered = False


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# LOGGER
# ============================================================

def get_logger():

    logger = logging.getLogger("athan_app")

    if not logger.handlers:

        logger.setLevel(logging.INFO)

        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.INFO)

        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )

        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        ch.setFormatter(
            logging.Formatter(
                "%(levelname)s: %(message)s"
            )
        )

        logger.addHandler(ch)

    return logger


logger = get_logger()


# ============================================================
# GLOBAL STATE
# ============================================================

prayers = {}
last_fetch_date = None
played_today = set()

athan_process = None
athan_lock = threading.Lock()

# Which prayer is currently playing
currently_playing_prayer = None

weather_cache = {
    "timestamp": 0,
    "data": None,
}


# ============================================================
# PRAYER TIMES
# ============================================================

def clean_prayer_time(value):

    match = re.search(
        r"(\d{1,2}):(\d{2})",
        str(value)
    )

    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"

    return None


def get_prayer_times():

    today_str = datetime.now(
        TIMEZONE
    ).strftime("%d-%m-%Y")

    url = (
        "https://api.aladhan.com/v1/timings"
        f"?latitude={LAT}"
        f"&longitude={LON}"
        f"&method={METHOD}"
        f"&date={today_str}"
    )

    try:

        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        timings = data["data"]["timings"]

        result = {}

        for prayer in PRAYERS:

            cleaned = clean_prayer_time(
                timings[prayer]
            )

            if cleaned:
                result[prayer] = cleaned

        if len(result) != len(PRAYERS):
            raise ValueError(
                "Not all prayer times were returned"
            )

        logger.info(
            "Fetched prayer times successfully."
        )

        return result

    except Exception as e:

        logger.warning(
            f"Failed to fetch prayer times: {e}"
        )

        return {
            "Fajr": "05:12",
            "Dhuhr": "12:15",
            "Asr": "15:30",
            "Maghrib": "18:45",
            "Isha": "20:00",
        }


def fetch_prayer_times_if_needed():

    global prayers
    global last_fetch_date

    today = datetime.now(
        TIMEZONE
    ).date()

    if last_fetch_date != today:

        prayers = get_prayer_times()

        last_fetch_date = today

        played_today.clear()

        logger.info(
            "Prayer times updated for today."
        )


# ============================================================
# NEXT PRAYER
# ============================================================

def get_next_prayer():

    now = datetime.now(TIMEZONE)

    fetch_prayer_times_if_needed()

    for name in PRAYERS:

        time_str = prayers.get(name)

        if not time_str:
            continue

        hour, minute = map(
            int,
            time_str.split(":")
        )

        prayer_time = now.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

        if prayer_time > now:

            seconds = int(
                (prayer_time - now).total_seconds()
            )

            return (
                name,
                prayer_time,
                seconds,
            )

    # All prayers passed.
    # Next prayer is tomorrow's Fajr.

    fajr_time = prayers.get(
        "Fajr",
        "05:12"
    )

    hour, minute = map(
        int,
        fajr_time.split(":")
    )

    tomorrow = now + timedelta(days=1)

    next_fajr = tomorrow.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    seconds = int(
        (next_fajr - now).total_seconds()
    )

    return (
        "Fajr",
        next_fajr,
        seconds,
    )


# ============================================================
# WEATHER
# ============================================================

def weather_description(code):

    descriptions = {

        0: ("Clear sky", "☀️"),
        1: ("Mainly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),

        45: ("Foggy", "🌫️"),
        48: ("Rime fog", "🌫️"),

        51: ("Light drizzle", "🌦️"),
        53: ("Drizzle", "🌦️"),
        55: ("Heavy drizzle", "🌧️"),

        56: ("Freezing drizzle", "🌧️"),
        57: ("Freezing drizzle", "🌧️"),

        61: ("Light rain", "🌦️"),
        63: ("Rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),

        66: ("Freezing rain", "🌧️"),
        67: ("Heavy freezing rain", "🌧️"),

        71: ("Light snow", "🌨️"),
        73: ("Snow", "🌨️"),
        75: ("Heavy snow", "❄️"),

        77: ("Snow grains", "❄️"),

        80: ("Light showers", "🌦️"),
        81: ("Showers", "🌧️"),
        82: ("Heavy showers", "⛈️"),

        85: ("Snow showers", "🌨️"),
        86: ("Heavy snow showers", "❄️"),

        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with hail", "⛈️"),
        99: ("Thunderstorm with heavy hail", "⛈️"),
    }

    return descriptions.get(
        code,
        ("Unknown", "🌡️")
    )


def get_weather():

    global weather_cache

    now = time.time()

    if (
        weather_cache["data"] is not None
        and now - weather_cache["timestamp"]
        < WEATHER_CACHE_SECONDS
    ):
        return weather_cache["data"]

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}"
        f"&longitude={LON}"
        "&current="
        "temperature_2m,"
        "relative_humidity_2m,"
        "apparent_temperature,"
        "weather_code,"
        "wind_speed_10m,"
        "is_day"
        "&temperature_unit=fahrenheit"
        "&wind_speed_unit=mph"
        "&timezone=America%2FNew_York"
    )

    try:

        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        current = data["current"]

        code = int(
            current["weather_code"]
        )

        description, icon = weather_description(
            code
        )

        result = {

            "city": CITY,

            "state": STATE,

            "temperature":
                round(
                    current["temperature_2m"]
                ),

            "feels_like":
                round(
                    current["apparent_temperature"]
                ),

            "humidity":
                round(
                    current["relative_humidity_2m"]
                ),

            "wind_speed":
                round(
                    current["wind_speed_10m"]
                ),

            "weather_code": code,

            "description": description,

            "icon": icon,

            "is_day":
                bool(current["is_day"]),

            "updated":
                current.get("time"),
        }

        weather_cache["timestamp"] = now

        weather_cache["data"] = result

        logger.info(
            "Weather updated successfully."
        )

        return result

    except Exception as e:

        logger.warning(
            f"Failed to fetch weather: {e}"
        )

        if weather_cache["data"] is not None:
            return weather_cache["data"]

        return {

            "city": CITY,
            "state": STATE,

            "temperature": "--",
            "feels_like": "--",
            "humidity": "--",
            "wind_speed": "--",

            "weather_code": 0,

            "description":
                "Weather unavailable",

            "icon": "🌡️",

            "is_day": True,

            "updated": None,
        }


# ============================================================
# ATHAN
# ============================================================

def try_play_athan(athan_file):

    try:

        if not os.path.exists(athan_file):

            logger.error(
                f"Athan file not found: {athan_file}"
            )

            return None

        logger.info(
            f"Starting Athan: {athan_file}"
        )

        process = subprocess.Popen(
            [
                "aplay",
                "-D",
                AUDIO_DEVICE,
                athan_file,
            ],

            stdout=subprocess.DEVNULL,

            stderr=subprocess.PIPE,
        )

        return process

    except Exception as e:

        logger.warning(
            f"Athan failed to start: {e}"
        )

        return None


def play_athan_file(
    athan_file,
    prayer_name,
):

    global athan_process
    global currently_playing_prayer

    with athan_lock:

        if athan_process is not None:

            if athan_process.poll() is None:

                logger.info(
                    "Athan already playing."
                )

                return False

        logger.info(
            f"Playing Athan for {prayer_name}"
        )

        currently_playing_prayer = prayer_name

        athan_process = try_play_athan(
            athan_file
        )

        # Retry once
        if (
            athan_process is None
            or athan_process.poll() is not None
        ):

            logger.info(
                "Retrying Athan once..."
            )

            athan_process = try_play_athan(
                athan_file
            )

        if athan_process is None:

            currently_playing_prayer = None

            return False

        return True


def play_athan():

    global played_today

    now_hm = datetime.now(
        TIMEZONE
    ).strftime("%H:%M")

    for name, time_str in prayers.items():

        if (
            now_hm == time_str
            and name not in played_today
        ):

            if name == "Fajr":

                athan_file = FAJR_ATHAN_FILE

            else:

                athan_file = random.choice(
                    ATHAN_FILES
                )

            if not os.path.exists(
                athan_file
            ):

                logger.error(
                    f"Athan file not found: {athan_file}"
                )

                played_today.add(name)

                return

            played_today.add(name)

            play_athan_file(
                athan_file,
                name,
            )

            break


# ============================================================
# TEST ATHAN
# ============================================================

def run_test_athan():

    global test_triggered

    if not TEST_MODE:
        return

    if test_triggered:
        return

    if test_start_time is None:
        return

    elapsed = (
        time.monotonic()
        - test_start_time
    )

    if elapsed < TEST_PRAYER_DELAY:
        return

    test_triggered = True

    logger.info(
        "======================================"
    )

    logger.info(
        "TEST MODE: Simulating prayer."
    )

    logger.info(
        f"TEST MODE: Prayer = {TEST_PRAYER_NAME}"
    )

    logger.info(
        "TEST MODE: Playing Athan now."
    )

    logger.info(
        "======================================"
    )

    if TEST_PRAYER_NAME == "Fajr":

        athan_file = FAJR_ATHAN_FILE

    else:

        athan_file = random.choice(
            ATHAN_FILES
        )

    play_athan_file(
        athan_file,
        TEST_PRAYER_NAME,
    )


# ============================================================
# STOP ATHAN
# ============================================================

def stop_athan():

    global athan_process
    global currently_playing_prayer

    with athan_lock:

        if athan_process is None:

            logger.info(
                "Stop requested but no Athan is playing."
            )

            return False

        try:

            if athan_process.poll() is None:

                logger.info(
                    "Stopping Athan."
                )

                athan_process.terminate()

                try:

                    athan_process.wait(
                        timeout=2
                    )

                except subprocess.TimeoutExpired:

                    logger.warning(
                        "Athan did not terminate. Killing it."
                    )

                    athan_process.kill()

            athan_process = None

            currently_playing_prayer = None

            return True

        except Exception as e:

            logger.warning(
                f"Failed to stop Athan: {e}"
            )

            athan_process = None

            currently_playing_prayer = None

            return False


def is_athan_playing():

    global athan_process
    global currently_playing_prayer

    if athan_process is None:
        return False

    if athan_process.poll() is None:
        return True

    athan_process = None

    currently_playing_prayer = None

    return False


# ============================================================
# BACKGROUND WORKER
# ============================================================

def athan_worker():

    logger.info(
        "Athan background worker started."
    )

    while True:

        try:

            fetch_prayer_times_if_needed()

            # Normal real prayer checking
            if not TEST_MODE:
                play_athan()

            # Test prayer
            if TEST_MODE:
                run_test_athan()

        except Exception as e:

            logger.exception(
                f"Background worker error: {e}"
            )

        time.sleep(1)


# ============================================================
# API ROUTES
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


@app.route("/api/status")
def status():

    fetch_prayer_times_if_needed()

    next_name, next_time, seconds = (
        get_next_prayer()
    )

    now = datetime.now(
        TIMEZONE
    )

    playing = is_athan_playing()

    # During the test, tell the UI which
    # simulated prayer is playing.
    if playing and currently_playing_prayer:

        display_prayer = (
            currently_playing_prayer
        )

    else:

        display_prayer = None

    # Test countdown information
    test_seconds_remaining = None

    if (
        TEST_MODE
        and test_start_time is not None
        and not test_triggered
    ):

        elapsed = (
            time.monotonic()
            - test_start_time
        )

        test_seconds_remaining = max(
            0,
            int(
                TEST_PRAYER_DELAY
                - elapsed
            )
        )

    return jsonify(
        {

            "city": CITY,

            "state": STATE,

            "country": COUNTRY,

            "date":
                now.strftime(
                    "%a, %d %b %Y"
                ),

            "time":
                now.strftime(
                    "%I:%M:%S %p"
                ),

            "timestamp":
                int(now.timestamp()),

            "prayers":
                prayers,

            "next_prayer": {

                "name": next_name,

                "time":
                    next_time.strftime(
                        "%I:%M %p"
                    ),

                "seconds":
                    seconds,
            },

            "athan_playing":
                playing,

            "currently_playing":
                display_prayer,

            # Testing information
            "test_mode":
                TEST_MODE,

            "test_triggered":
                test_triggered,

            "test_prayer":
                TEST_PRAYER_NAME,

            "test_seconds_remaining":
                test_seconds_remaining,
        }
    )


@app.route("/api/weather")
def weather_api():

    return jsonify(
        get_weather()
    )


@app.route(
    "/api/stop-athan",
    methods=["POST"]
)
def stop_athan_api():

    stopped = stop_athan()

    return jsonify(
        {
            "success": True,
            "stopped": stopped,
        }
    )


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":

    global_test_start = None

    logger.info(
        f"Delaying app start by "
        f"{START_DELAY} seconds..."
    )

    time.sleep(
        START_DELAY
    )

    fetch_prayer_times_if_needed()

    get_weather()

    # Start test timer AFTER the startup delay.
    if TEST_MODE:

        test_start_time = time.monotonic()

        logger.info(
            "TEST MODE ENABLED."
        )

        logger.info(
            f"Test prayer will play in "
            f"{TEST_PRAYER_DELAY} seconds."
        )

    worker = threading.Thread(
        target=athan_worker,
        daemon=True,
    )

    worker.start()

    logger.info(
        "Starting Athan web server."
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True,
        use_reloader=False,
    )