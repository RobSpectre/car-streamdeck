import re
import os
import json

from datetime import datetime
from datetime import timedelta

from collections import deque

import click
import yagmail

import geocoder

import requests

labels = {
    'PD': {
        'short_label': 'PD',
        'long_label': 'Police Department',
        'location_key': 'city'
    },
    'Unmarked': {
        'short_label': 'Unmarked',
        'long_label': 'Unmarked Unit',
        'location_key': 'county'
    },
    'State': {
        'short_label': 'State',
        'long_label': 'State Trooper',
        'location_key': 'state'
    },
    'Sheriff': {
        'short_label': 'Sheriff',
        'long_label': 'County Sheriff',
        'location_key': 'county'
    },
    'FalsePositive': {
        'short_label': 'FalsePositive',
        'long_label': 'False Positive',
        'location_key': 'city'
    },
    'OtherLE': {
        'short_label': 'OtherLE',
        'long_label': 'Other Law Enforcement Unit',
        'location_key': 'city'
    },
    'FalseNegative': {
        'short_label': 'FalseNegative',
        'long_label': 'False Negative',
        'location_key': 'city'
    },
    'EMS': {
        'short_label': 'EMS',
        'long_label': 'Emergency Response Vehicle (non-LE)',
        'location_key': 'city'
    }
}

time_pattern = r'time (\d{2}:\d{2}:\d{2}[apmAPM]{2})'
date_pattern = r'date (\d{4}/\d{2}/\d{2})'

now = datetime.now()
now_string = now.strftime("%d %B %Y - %I:%M:%S%p")

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)


@click.group()
def cli():
    pass


@cli.command(help="Send data report to Sherlock HQ.", name="send")
@click.option("--to", required=True, type=str,
              help="Recipient of data report.")
@click.option("--sender", required=True, type=str,
              help="Sender of data report.")
@click.option("--agency", required=True, type=str,
              help="Agency of vehicle reported.")
def send(to, sender, agency):
    click.echo("Sending report...")
    yag = yagmail.SMTP(sender)
    contents = []
    subject = ""

    location = get_location()

    click.echo(f"Location: {location}")

    if location:
        subject = f"Sherlock data log for {labels[agency]['long_label']} in " \
                  f"{location[labels[agency]['location_key']]" \
                  f"at {now_string}"

        contents.append("AMIGO!")
        contents.append(f"Found a {labels[agency]['long_label']} unit - here is the info:")
        contents.append("<h1>Data Report</h1>")

        map_image_uri = "https://maps.googleapis.com/maps/api/staticmap?center=" \
                        f"{location['lat']},{location['lon']}" \
                        "&zoom=14&size=400x400&markers=color:blue%7Clabel:P%7C" \
                        f"{location['lat']},{location['lon']}" \
                        f"&key={GOOGLE_API_KEY}"

        contents.append(f"\n<img src=\"{map_image_uri}\"></img>\n")

        contents.append(f"""
                      Latitude: {location['lat']}
                      Longitude: {location['lon']}
                      Speed: {location['speed']}
                      City: {location['city']}
                      County: {location['county']}
                      State: {location['state']}
                      Time: {location['time']}""")
    else:
        subject = f"Sherlock data log for {labels[agency]['long_label']} at {now_string}"
        contents.append("AMIGO!")
        contents.append(f"Found a {labels[agency]['long_label']} unit, but could not find location.")
        contents.append("I'll respond later with where this occured.")

    lines = get_data_logs()

    if len(lines) > 0:
        contents.append("<h2>Data Log:</h2>")
        contents.append("<pre><code>")

        for line in lines:
            contents.append(line)

        contents.append("</code></pre>")
    else:
        contents.append("<pre>No data associated with this timestamp.</pre>")

    try:
        yag.send(to=to,
                 subject=subject,
                 contents=contents)
    except Exception as e:
        click.echo(f"Error sending email: {e}")

    click.echo("Writing data log...")

    write_data_logs(agency, location, lines)

    click.echo("Done.")


def get_location():
    click.echo("Getting location...")

    current = get_gps_coordinates()

    if current:
        address = get_address(current)
    else:
        return None

    if address:
        return {
            'lat': current['lat'],
            'lon': current['lon'],
            'speed': current['speed'],
            'altitude': current['alt'],
            'track': current['track'],
            'city': address.city,
            'county': address.county,
            'state': address.state,
            'time': now_string
        }
    else:
        return None


def get_gps_coordinates():
    current = None

    try:
        current = requests.get('http://localhost:8000/location').json()
    except Exception as e:
        click.echo(f"Unable to get location: {e}")
    finally:
        if current and current['mode'] > 1:
            click.echo("Fix acquired: {0}, {1}".format(current['lat'],
                                                       current['lon']))

            return current
        else:
            click.echo("Unable to acquire fix.")

    return None


def get_address(current):
    address = None

    try:
        address = geocoder.google([current['lat'], current['lon']],
                                  method='reverse')
        click.echo(f"Address acquired: {address}")
        click.echo("KEY: {0}".format(os.environ.get('GOOGLE_API_KEY', None)))
    except Exception as e:
        click.echo("Could not reverse address: {0}".format(e))

    return address


def get_data_logs():
    lines = []

    with open('/var/www/html/DetectData.txt', 'r') as f:
        last_20_lines = deque(f, 20)

    for line in last_20_lines:
        date_match = re.search(date_pattern, line)
        time_match = re.search(time_pattern, line)

        if date_match and time_match:
            timestamp_string = f"{date_match.group(1)} {time_match.group(1)}"
            timestamp = datetime.strptime(timestamp_string, "%Y/%m/%d %I:%M:%S%p")

            time_difference = now - timestamp

            if abs(time_difference) <= timedelta(minutes=5):
                lines.append(line)

    return lines


def write_data_logs(agency, location, lines):
    with open("sherlock.jsonl", "a") as file:
        for line in lines:
            frame = {
                'agency': agency,
                'location': location,
                'data': line
            }

            string = json.dumps(frame)
            file.write(string + "\n")


if __name__ == "__main__":
    cli()
