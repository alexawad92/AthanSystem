import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
import random
from kivy.uix.anchorlayout import AnchorLayout

# ---------------------
# Configuration
# ---------------------
LOG_FILE = "/home/alexawad/AthanSystem/AthanSystem/athan.log"
LAT = 35.947789
LON = -84.174276
METHOD = 2
TIMEZONE = ZoneInfo("America/New_York")
PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
ATHAN_FILES = ["assets/Athan1.wav", "assets/Athan2.wav"]
BG_IMAGE = "assets/Background.jpg"
START_DELAY = 30  # seconds to delay app start

# ---------------------
# Logger Setup
# ---------------------
def get_logger():
    logger = logging.getLogger("athan_app")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)
    return logger

logger = get_logger()

# ---------------------
# Fetch prayer times
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
# Next prayer
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
# Custom Root Layout
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
        self.played_today = set()  # track prayers already played

        root = RootLayout()

        # Background
        bg = Image(source=BG_IMAGE, allow_stretch=True, keep_ratio=False)
        bg.size_hint = (1, 1)
        root.add_widget(bg)

        # Overlay layout
        self.overlay = BoxLayout(orientation='vertical', padding=50, spacing=9,
                                 size_hint=(1,1))
        root.add_widget(self.overlay)

        # ---------------------
        # Top row: date (left) and time (right)
        # ---------------------
        top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)

        self.date_label = Label(text="", font_size=32, color=(1,1,1,1), halign="left")
        self.time_label = Label(text="", font_size=32, color=(1,1,1,1), halign="right")

        top_row.add_widget(self.date_label)
        top_row.add_widget(self.time_label)

        self.overlay.add_widget(top_row)

        # Next prayer countdown (middle row)
        self.next_label = Label(text="", font_size=42, color=(1,1,1,1))
        self.overlay.add_widget(self.next_label)

       

        # ---------------------
        # Prayer times rows
        # ---------------------

        # Top row: Fajr, Dhuhr, Asr
        self.prayer_top_row = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=80)
        self.overlay.add_widget(self.prayer_top_row)

        # Bottom row: Maghrib, Isha
        self.prayer_bottom_row = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=80)
        self.overlay.add_widget(self.prayer_bottom_row)

        # Create labels
        self.prayer_labels = []

        for i, name in enumerate(PRAYERS):
            lbl = Label(text="", font_size=32, color=(1,1,1,1))
            self.prayer_labels.append(lbl)
            if i < 3:
                self.prayer_top_row.add_widget(lbl)
            else:
                self.prayer_bottom_row.add_widget(lbl)

        # Schedule update loop
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
            self.played_today.clear()  # reset for new day
            logger.info("Prayer times updated for today.")

    # ---------------------
    # Update every second
    # ---------------------
    def update(self, dt):
        # Update current time
        now = datetime.now(TIMEZONE)
        now_time_ampm = now.strftime("%I:%M:%S %p")  # "03:30:45 PM"
        self.time_label.text = now_time_ampm

        self.fetch_prayer_times_if_needed()

        # Update countdown
        next_name, countdown = next_prayer(self.prayers)
        self.next_label.text = f"Next Prayer: {next_name}\n{countdown}"

        # Update current date
        now = datetime.now(TIMEZONE)
        self.date_label.text = now.strftime("%a, %d %b %Y")

        # Update prayer row
        for i, name in enumerate(PRAYERS):
            p_time_24 = self.prayers[name]          # e.g., "15:30"
            p_time_obj = datetime.strptime(p_time_24, "%H:%M")
            p_time_ampm = p_time_obj.strftime("%I:%M %p")  # "03:30 PM"

            self.prayer_labels[i].text = f"{name}\n{p_time_ampm}"    

        # Play Athan if it's prayer time
        self.play_athan()

    # ---------------------
    # Play Athan
    # ---------------------
    def play_athan(self):
        now_hm = datetime.now(TIMEZONE).strftime("%H:%M")
        for name, time_str in self.prayers.items():
            if now_hm == time_str and name not in self.played_today:
                athan_file = random.choice(ATHAN_FILES)
                if not os.path.exists(athan_file):
                    logger.error(f"Athan file not found: {athan_file}")
                    return

                self.on = True
                self.played_today.add(name)  # mark as played
                logger.info(f"Playing Athan for {name}")

                def try_play():
                    try:
                        proc = subprocess.Popen(
                            ["aplay", "-D", "plughw:1,0", athan_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE
                        )
                        return proc
                    except Exception as e:
                        logger.warning(f"Athan failed to start: {e}")
                        return None

                # First attempt
                self.athan_process = try_play()

                # Retry once if first attempt failed or immediately exited
                if self.athan_process is None or self.athan_process.poll() is not None:
                    logger.info("Retrying Athan once...")
                    self.athan_process = try_play()

                # Schedule reset after 30s
                def reset_flag(dt):
                    self.on = False
                    self.athan_process = None
                    logger.info("Athan finished")

                Clock.schedule_once(reset_flag, 30)
                break  # only play one prayer at a time

    def handle_touch(self, touch):
        logger.info("Screen touched")
        if self.athan_process:
            logger.info("Stopping Athan due to touch")
            try:
                self.athan_process.terminate()
                self.athan_process.wait(timeout=2)  # wait for proper termination
            except Exception as e:
                logger.warning(f"Failed to terminate Athan: {e}")

            self.athan_process = None
            self.on = False
        else:
            logger.info("No Athan playing on touch")

# ---------------------
# Main entry
# ---------------------
if __name__ == "__main__":
    from kivy.core.window import Window
    Window.fullscreen = "auto"

    logger.info(f"Delaying app start by {START_DELAY} seconds...")
    time.sleep(START_DELAY)

    logger.info("Starting AthanClockApp")
    AthanClockApp().run()
    logger.info("AthanClockApp exited")
