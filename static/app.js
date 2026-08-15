// ============================================================
// ATHAN CLOCK FRONTEND
// ============================================================

let statusData = null;
let weatherData = null;

let countdownSeconds = 0;
let lastNextPrayer = "";


// ============================================================
// HELPERS
// ============================================================

function formatCountdown(totalSeconds) {

    totalSeconds = Math.max(0, Math.floor(totalSeconds));

    const hours = Math.floor(totalSeconds / 3600);

    const minutes = Math.floor(
        (totalSeconds % 3600) / 60
    );

    const seconds = totalSeconds % 60;

    return (
        String(hours).padStart(2, "0") +
        ":" +
        String(minutes).padStart(2, "0") +
        ":" +
        String(seconds).padStart(2, "0")
    );
}


function formatPrayerTime(time24) {

    if (!time24) {
        return "--";
    }

    const parts = time24.split(":");

    let hour = parseInt(parts[0]);
    const minute = parts[1];

    const ampm = hour >= 12 ? "PM" : "AM";

    hour = hour % 12;

    if (hour === 0) {
        hour = 12;
    }

    return `${hour}:${minute} ${ampm}`;
}


// ============================================================
// UPDATE CLOCK
// ============================================================

function updateClock() {

    const now = new Date();

    let hours = now.getHours();

    const minutes = String(
        now.getMinutes()
    ).padStart(2, "0");

    const seconds = String(
        now.getSeconds()
    ).padStart(2, "0");

    const ampm = hours >= 12 ? "PM" : "AM";

    hours = hours % 12;

    if (hours === 0) {
        hours = 12;
    }

    hours = String(hours).padStart(2, "0");

    document.getElementById("time").textContent =
        `${hours}:${minutes}:${seconds} ${ampm}`;

}


// ============================================================
// UPDATE COUNTDOWN
// ============================================================

function updateCountdown() {

    if (!statusData) {
        return;
    }

    const now = Math.floor(
        Date.now() / 1000
    );

    const elapsed =
        now - statusData.timestamp;

    const remaining =
        statusData.next_prayer.seconds - elapsed;

    countdownSeconds = Math.max(
        0,
        remaining
    );

    document.getElementById(
        "countdown"
    ).textContent =
        formatCountdown(countdownSeconds);
}


// ============================================================
// STATUS
// ============================================================

async function fetchStatus() {

    try {

        const response =
            await fetch(
                "/api/status",
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                "Status request failed"
            );
        }

        statusData =
            await response.json();

        updateStatusUI();

    } catch (error) {

        console.error(
            "Status error:",
            error
        );

    }
}


function updateStatusUI() {

    if (!statusData) {
        return;
    }


    // Location

    document.getElementById(
        "city"
    ).textContent =
        statusData.city;

    document.getElementById(
        "state"
    ).textContent =
        statusData.state;


    // Date

    const date =
        new Date();

    document.getElementById(
        "date"
    ).textContent =
        date.toLocaleDateString(
            "en-US",
            {
                weekday: "short",
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );


    // Next prayer

    document.getElementById(
        "next-prayer-name"
    ).textContent =
        statusData.next_prayer.name;


    document.getElementById(
        "next-prayer-time"
    ).textContent =
        statusData.next_prayer.time;


    // Prayer times

    for (
        const prayer of [
            "Fajr",
            "Dhuhr",
            "Asr",
            "Maghrib",
            "Isha"
        ]
    ) {

        const element =
            document.getElementById(
                `prayer-${prayer}`
            );

        if (
            element &&
            statusData.prayers[prayer]
        ) {

            element.textContent =
                formatPrayerTime(
                    statusData.prayers[prayer]
                );
        }
    }


    // Highlight next prayer

    document
        .querySelectorAll(".prayer-card")
        .forEach(card => {

            card.classList.remove(
                "active"
            );

            if (
                card.dataset.prayer ===
                statusData.next_prayer.name
            ) {

                card.classList.add(
                    "active"
                );
            }

        });


    // Athan overlay

    updateAthanOverlay(
        statusData.athan_playing
    );
}


// ============================================================
// WEATHER
// ============================================================

async function fetchWeather() {

    try {

        const response =
            await fetch(
                "/api/weather",
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                "Weather request failed"
            );
        }

        weatherData =
            await response.json();

        updateWeatherUI();

    } catch (error) {

        console.error(
            "Weather error:",
            error
        );

    }
}


function updateWeatherUI() {

    if (!weatherData) {
        return;
    }


    document.getElementById(
        "temperature"
    ).textContent =
        weatherData.temperature;


    document.getElementById(
        "feels-like"
    ).textContent =
        weatherData.feels_like;


    document.getElementById(
        "humidity"
    ).textContent =
        weatherData.humidity;


    document.getElementById(
        "wind"
    ).textContent =
        weatherData.wind_speed;


    document.getElementById(
        "weather-description"
    ).textContent =
        weatherData.description;


    document.getElementById(
        "weather-icon"
    ).textContent =
        weatherData.icon;
}


// ============================================================
// ATHAN OVERLAY
// ============================================================

function updateAthanOverlay(isPlaying) {

    const overlay =
        document.getElementById(
            "athan-overlay"
        );

    const prayerName =
        document.getElementById(
            "athan-prayer"
        );


    if (isPlaying) {

        if (
            statusData &&
            statusData.next_prayer
        ) {
            prayerName.textContent =
                "Athan";
        }

        overlay.classList.remove(
            "hidden"
        );

    } else {

        overlay.classList.add(
            "hidden"
        );
    }
}


// ============================================================
// STOP ATHAN
// ============================================================

async function stopAthan() {

    try {

        await fetch(
            "/api/stop-athan",
            {
                method: "POST"
            }
        );

        await fetchStatus();

    } catch (error) {

        console.error(
            "Failed to stop Athan:",
            error
        );
    }
}


document
    .getElementById("stop-athan")
    .addEventListener(
        "click",
        stopAthan
    );


// Allow tapping anywhere on the screen
// to stop the Athan.

document.addEventListener(
    "click",
    function(event) {

        const overlay =
            document.getElementById(
                "athan-overlay"
            );

        if (
            !overlay.classList.contains(
                "hidden"
            )
        ) {

            if (
                event.target.id !==
                "stop-athan"
            ) {
                stopAthan();
            }
        }

    }
);


// ============================================================
// INITIALIZATION
// ============================================================

async function initialize() {

    updateClock();

    await fetchStatus();

    await fetchWeather();

    updateCountdown();
}


// ============================================================
// TIMERS
// ============================================================

// Clock

setInterval(
    updateClock,
    1000
);


// Countdown

setInterval(
    updateCountdown,
    1000
);


// Status from Python

setInterval(
    fetchStatus,
    3000
);


// Weather

setInterval(
    fetchWeather,
    10 * 60 * 1000
);


// Start

initialize();