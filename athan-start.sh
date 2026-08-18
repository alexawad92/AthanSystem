#!/bin/bash

LOG="$HOME/AthanSystem/AthanSystem/athan-audio-startup.log"

echo "========================================" >> "$LOG"
echo "$(date) Starting Athan frontend" >> "$LOG"

# Graphical display
export DISPLAY=:0

# Wait for PipeWire/WirePlumber and Bluetooth
sleep 8

echo "$(date) PipeWire status before audio setup:" >> "$LOG"
wpctl status >> "$LOG" 2>&1

# ============================================================
# BLUETOOTH SPEAKER
# ============================================================

# Find the Bluetooth speaker by name.
# Do NOT hard-code the PipeWire ID because it can change after reboot.
BT_SINK=$(wpctl status | grep "CPP-4303" | grep -oE '[0-9]+\.' | head -1 | tr -d '.')

echo "$(date) Detected Bluetooth speaker sink ID: '$BT_SINK'" >> "$LOG"

if [[ "$BT_SINK" =~ ^[0-9]+$ ]]; then

    echo "$(date) Bluetooth speaker found: $BT_SINK" >> "$LOG"

    # Make Bluetooth speaker the default output
    wpctl set-default "$BT_SINK" >> "$LOG" 2>&1

    # Set volume to 80%
    wpctl set-volume "$BT_SINK" 1.0 >> "$LOG" 2>&1

    # Make sure it is not muted
    wpctl set-mute "$BT_SINK" 0 >> "$LOG" 2>&1

    echo "$(date) Bluetooth speaker configured as default" >> "$LOG"

else

    echo "$(date) ERROR: Bluetooth speaker CPP-4303 not found" >> "$LOG"

    echo "$(date) Available sinks:" >> "$LOG"
    wpctl status >> "$LOG" 2>&1

fi

# ============================================================
# WAIT FOR AUDIO TO SETTLE
# ============================================================

sleep 2

echo "$(date) Final audio status:" >> "$LOG"
wpctl status >> "$LOG" 2>&1

# ============================================================
# START CHROMIUM
# ============================================================

echo "$(date) DISPLAY=$DISPLAY" >> "$LOG"
echo "$(date) Starting Chromium" >> "$LOG"

chromium --kiosk http://localhost:5000 >> "$LOG" 2>&1
