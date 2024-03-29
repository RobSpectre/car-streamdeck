import os
import subprocess
import logging.config

from typing import Optional

from fastapi import FastAPI

from pydantic import BaseModel

import geocoder


class Location(BaseModel):
    mode: int
    alt: Optional[float] = None
    track: Optional[float] = None
    speed: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class State(BaseModel):
    current_location: Optional[Location] = None
    interval: int
    interval_limit: int
    counter: int
    current_state: Optional[str] = None


app = FastAPI()

app.current_location = None
app.interval = 1
app.interval_limit = 300
app.counter = 0
app.current_state = None

app.GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__)

try:
    with open('/var/www/html/ReadState.txt') as file:
        app.current_state = file.read()
except Exception as e:
    logger.error(f"Unable to read Sherlock state on startup: {e}")


@app.get("/location")
async def location():
    return app.current_location


@app.get("/state")
async def state():
    return State(
        current_location=app.current_location,
        interval=app.interval,
        interval_limit=app.interval_limit,
        counter=app.counter,
        current_state=app.current_state
    )


@app.put("/location")
async def create_location(location: Location):
    app.current_location = location

    app.counter += app.interval
    if app.counter > app.interval_limit and location.mode > 1:
        app.counter = 0

        update_sherlock_state(location)

    return app.current_location


def update_sherlock_state(location: Location):
    address = None

    try:
        address = geocoder.google([location.lat, location.lon],
                                  method='reverse')
    except Exception as e:
        logger.error(f"Could not reverse address: {e}")

    if address and (address.state != app.current_state):
        write_sherlock_state_and_refresh(address)

    return address


def write_sherlock_state_and_refresh(address):
    app.current_state = address.state

    try:
        with open('/var/www/html/ReadState.txt', 'w') as file:
            file.write(address.state)
    except Exception as e:
        logger.error(f"Could not write to Sherlock state file: {e}")

    try:
        subprocess.call(["./press_shortcut.sh",
                         "F5",
                         "Mozilla"])
    except Exception as e:
        logger.error(f"Could not refresh Sherlock window: {e}")

    return app.current_state
