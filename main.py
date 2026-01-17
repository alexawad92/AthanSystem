import logging
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

# ---------------------
# Configuration
# ---------------------
LOG_FILE = "/home/alexawad/AthanSystem/AthanSystem/athan.log"
LAT = 35.947789   # Knoxville lat
LON = -84.174276  # Knoxville lon
METHOD = 2
TIMEZONE = ZoneInfo("America/New_York")
PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
ATHAN_FILE = "assets/Athan1.wav"
BG_IMAGE = "assets/Background.jpg"


# ---------------------
# Logger Setup
# ---------------------
def get_logger():
    logger = logging.getLogger("athan_app")
    if not logger.handlers:  # prevent duplicate handlers
        logger.setLevel(logging.INFO)

        # File handler
        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)
    return logger

logger = get_logger()


# ---------------------
# Fetch Prayer Times
# ---------------------
def get_prayer_times():
    today_str = datetime.now(TIMEZONE).strftime("%d-%m-%Y")
    url = f"http://api.aladhan.com/v1/timings?latitude={LAT}&longitude={LON}&method={METHOD}&date={today_str}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        timings = data['data']['timings']
        prayers = {k: timings[k] for k in PRAYERS}
        logger.info("Fetched prayer times successfully.")
        return prayers
    except Exception as e:
        logger.warning(f"Failed to fetch prayer times: {e}")
        # fallback times
        return {"Fajr": "05:12", "Dhuhr": "12:15", "Asr": "15:30", "Maghrib": "18:45", "Isha": "20:00"}


# ---------------------
# Next Prayer
# ---------------------
def next_prayer(prayers):
    now = datetime.now(TIMEZONE)
    for name, time_str in prayers.items():
        p_time = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=TIMEZONE
        )
        if p_time > now:
            delta = p_time - now
            return name, str(delta).split(".")[0]
    return "Fajr", "00:00:00"


# ---------------------
# Custom Root to detect touches
# ---------------------
class RootLayout(FloatLayout):
    def on_touch_down(self, touch):
        app = App.get_running_app()
        if hasattr(app, "handle_touch"):
            app.handle_touch(touch)
        return super().on_touch_down(touch)


# ---------------------
# Kivy App
# ---------------------
class AthanClockApp(App):
    def build(self):
        self.on = False
        self.athan_process = None
        self.prayers = {}
        self.last_fetch_date = None

        # fetch prayer times initially
        self.fetch_prayer_times_if_needed()

        root = RootLayout()

        # Background fills entire screen
        bg = Image(source=BG_IMAGE, allow_stretch=True, keep_ratio=False)
        bg.size_hint = (1, 1)
        bg.pos = (0, 0)
        root.add_widget(bg)

        # Overlay layout
        self.overlay = BoxLayout(
            orientation='vertical', padding=50, spacing=9,
            size_hint=(1, 1), pos=(0, 0)
        )
        root.add_widget(self.overlay)

        # Next prayer countdown
        self.next_label = Label(text="", font_size=60, color=(1,1,1,1))
        self.overlay.add_widget(self.next_label)

        # Current date
        self.date_label = Label(text="", font_size=35, color=(1,1,1,1))
        self.overlay.add_widget(self.date_label)

        # Prayers row
        self.prayers_row = GridLayout(cols=6, size_hint_y=0.9, spacing=10)
        self.overlay.add_widget(self.prayers_row)
        self.prayer_labels = []
        for name in PRAYERS:
            lbl = Label(text="", font_size=40, color=(1,1,1,1))
            self.prayers_row.add_widget(lbl)
            self.prayer_labels.append(lbl)

        # Schedule updates every second
        Clock.schedule_interval(self.update, 1)
        return root

    # ---------------------
    # Fetch prayer times once per day
    # ---------------------
    def fetch_prayer_times_if_needed(self):
        today = datetime.now(TIMEZONE).date()
        if self.last_fetch_date != today:
            self.prayers = get_prayer_times()
            self.last_fetch_date = today
            logger.info("Prayer times updated for today.")

    # ---------------------
    # Update labels every second
    # ---------------------
    def update(self, dt):
        # Update prayer times if day changed
        self.fetch_prayer_times_if_needed()

        # Update countdown
        next_name, countdown = next_prayer(self.prayers)
        self.next_label.text = f"Next Prayer: {next_name}\n{countdown}"

        # Update current date
        now = datetime.now(TIMEZONE)
        self.date_label.text = now.strftime("%a, %d %b %Y")

        # Update prayer times row
        for i, name in enumerate(PRAYERS):
            self.prayer_labels[i].text = f"{name}\n{self.prayers[name]}"

        # Play Athan at exact time
        self.play_athan()

    # ---------------------
    # Play Athan
    # ---------------------
    def play_athan(self):
        now = datetime.now(TIMEZONE).strftime("%H:%M")
        for name, time_str in self.prayers.items():
            if now == time_str and not self.on:
                logger.info(f"time for prayer")
                if not os.path.exists(ATHAN_FILE):
                    logger.error(f"Athan file not found: {ATHAN_FILE}")
                    return

                self.on = True
                logger.info(f"Playing Athan for {name}")
                self.athan_process = subprocess.Popen(
                    ["aplay", "-D", "plughw:1,0", ATHAN_FILE],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # Reset flag after ~30 seconds
                def reset_flag(dt):
                    self.on = False
                    self.athan_process = None
                    logger.info("Athan finished")
                Clock.schedule_once(reset_flag, 30)

    # ---------------------
    # Handle touches
    # ---------------------
    def handle_touch(self, touch):
        logger.info("Screen touched")
        if self.athan_process:
            logger.info("Stopping Athan due to touch")
            self.athan_process.terminate()
            self.athan_process = None
            self.on = False


# ---------------------
# Run App
# ---------------------
if __name__ == "__main__":
    from kivy.core.window import Window
    Window.fullscreen = "auto"
    logger.info("Starting AthanClockApp")
    AthanClockApp().run()
    logger.info("AthanClockApp exited")
