#!/usr/bin/python
import time
from datetime import datetime
import logging
import subprocess
import json

from daemon import DaemonContext

import gpsd

import geocoder

logger = logging.getLogger("LocationDaemon")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh = logging.FileHandler("./location.log")
logger.addHandler(fh)


class App:
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/tmp/location_daemon.pid'
        self.pidfile_timeout = 5

        self.interval = 1
        self.interval_counter = 0
        self.interval_limit = 300

        self.location = None

    def run(self):
        logging.info("Launching...")
        while True:
            now = datetime.now()
            now_string = now.strftime("%d %B %Y - %I:%M:%S%p")

            current = self.get_coordinates()

            if current and current.mode > 1:
                self.write_location(current, now_string)

            self.interval_counter += 1

            if self.interval_counter >= self.interval_limit:
                self.interval_counter = 0
                
                location = self.get_address(current)

                if location.state is not self.location.state:
                    self.write_state(location)
                    self.refresh_sherlock()

                    self.location = location

            time.sleep(self.interval)

    def get_coordinates(self):
        current = None

        try:
            logging.info("Connecting to GPSD...")

            gpsd.connect()
        except Exception as e:
            logging.info(f"Could not connect to GPSD: {e}")
            
            return None

        for i in range(5):
            try:
                current = gpsd.get_current()
                position = current.position()
            except Exception as e:
                logging.info(f"Attempt {i} - unable to get location: {e}")
            finally:
                if current.mode > 1:
                    logger.info(f"Fix acquired: ")
                                 "{current.lat}, "
                                 "{current.lon}")
                    
                    return current
                else:
                    logging.info(f"Unable to acquire fix: "
                                 "{current.mode}")

        return None

    def get_address(self, current):
        address = None

        try:
            address = geocoder.google([current.lat, current.lon],
                                      method='reverse')
        except Exception as e:
            logger.info("Could not reverse address: {0}".format(e))

        return address

    def write_state(self, location):
        logger.info("New state: updating Sherlock...")

        try:
            with open('/var/www/html/ReadState.txt', 'w') as f:
                f.write(location.state)
        except Exception as e:
            logging.error(f"Could not open state file: {e}")

    def refresh_sherlock(self):
        logging.info("Refreshing Sherlock...")

        subprocess.check_call("./press_shortcut.sh F5 Sherlock",
                              shell=True)

    def write_location(self, current, now_string):
        with open("location.json", "w") as file:
            coordinates = {
                "time": now_string,
                "lat": current.lat,
                "lon": current.lon
            }

            string = json.dumps(coordinates)
            file.write(string)


if __name__ == "__main__":
    app = App()
    daemon_runner = runner.DaemonRunner(App)
    daemon_runner.do_action()
