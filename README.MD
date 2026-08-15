Athan System

Athan prayer display system running on a Raspberry Pi.

Running Manually

To run the application manually from the host system.

1. SSH into the Raspberry Pi
ssh <username>@<raspberry-pi-ip>
2. Navigate to the application directory
cd /path/to/AthanSystem
3. Activate the Python virtual environment
source venv/bin/activate
4. Set the display
export DISPLAY=:0
5. Start the backend
python main.py

Keep this SSH session running.

6. Start Chromium

Open a new SSH session and repeat steps 1–4:

ssh <username>@<raspberry-pi-ip>
cd /path/to/AthanSystem
source venv/bin/activate
export DISPLAY=:0

Then start Chromium:

chromium --kiosk http://localhost:5000
7. Access the Application From Another Computer

The frontend can also be accessed from a browser on the local network:

http://<raspberry-pi-ip>:5000/
Automatic Startup

The application is configured to start automatically when the Raspberry Pi boots.

Backend

The Flask/Python backend runs as a systemd service:

athan.service

To check its status:

sudo systemctl status athan

After rebooting the Raspberry Pi, the service should automatically start.

Start
sudo systemctl start athan
Stop
sudo systemctl stop athan
Restart
sudo systemctl restart athan
Check Status
sudo systemctl status athan
View Live Logs
sudo journalctl -u athan -f

The service runs the backend using the project's Python virtual environment:

/path/to/AthanSystem/venv/bin/python
Frontend / Chromium

Chromium is configured to start automatically when the Raspberry Pi graphical desktop starts.

The autostart configuration is located at:

~/.config/autostart/athan-chromium.desktop

It launches Chromium in kiosk mode and opens:

http://localhost:5000

This allows the Raspberry Pi to operate as a dedicated Athan display without requiring Chromium to be started manually.

Application Location

The main application directory is:

/path/to/AthanSystem

Important files:

main.py
requirements.txt
run_athan.sh
athan.log


assets/
    Athan1.wav
    Athan2.wav
    Athan3.wav
    Fajr.wav


static/
    app.js
    style.css


templates/
    index.html


venv/
Network Access

From another device on the same network:

http://<raspberry-pi-ip>:5000/

The Raspberry Pi itself uses:

http://localhost:5000/
Troubleshooting
Check Whether the Backend Is Running
sudo systemctl status athan

The service should show:

Active: active (running)
Check Backend Logs
sudo journalctl -u athan -n 50

For live logs:

sudo journalctl -u athan -f
Check Whether Chromium Is Running
pgrep -a chromium
Restart the Backend
sudo systemctl restart athan
Reboot the Raspberry Pi
sudo reboot

After reboot, the backend should start automatically and Chromium should launch from the desktop autostart configuration.

Project Notes

The backend uses Flask and runs inside the project's Python virtual environment.

Prayer times are retrieved using the Aladhan API.

Weather information is retrieved using Open-Meteo.

Athan audio is played through the configured ALSA audio device:

plughw:1,0

The application is configured for:

City: Knoxville, Tennessee
Timezone: America/New_York
Prayer calculation method: Aladhan method 2
Development / Testing

The application contains a temporary test mode for testing the Athan audio and UI.

In main.py:

TEST_MODE = True

When enabled, the application simulates a prayer after the configured test delay.

For normal operation, make sure this is disabled:

TEST_MODE = False

The test settings are:

TEST_PRAYER_DELAY = 30
TEST_PRAYER_NAME = "Maghrib"

This causes a simulated Maghrib Athan to play 30 seconds after the application starts.