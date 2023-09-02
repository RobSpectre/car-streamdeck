import click
import gpsd
import yagmail
from geopy.geocoders import Nominatim


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

    if location:
        subject = f"Sherlock data log for {agency} in {location['city']}, {location['state']}"

        contents.append("AMIGO!")
        contents.append(f"Found a {agency} unit - here is the info:")
        contents.append(f"""
                      Location: <a href="{location['map_url']}">Location</a>
                      Latitude: {location['lat']}
                      Longitude: {location['lon']}
                      Speed: {location['speed']}
                      City: {location['city']}
                      County: {location['county']}
                      State: {location['state']}
                      Time: {location['time']}""")
    else:
        subject = f"Sherlock data log for {agency}"
        contents.append("AMIGO!")
        contents.append(f"Found a {agency} unit, but could not find location.")
        contents.append("I'll respond later with where this occured.")

    yag.send(to=to,
             subject=subject,
             contents=contents,
             attachments='/var/www/html/DetectData.txt')

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
            lat: current.lat,
            lon: current.lon,
            speed: current.speed(),
            altitude: current.alt,
            city: location.raw['address']['city'],
            county: location.raw['address']['county'],
            state: location.raw['address']['state'],
            time: current.time_local(),
            map_url: current.map_url
        }
    else:
        return None

def get_gps_coordinates():
    current = None

    try:
        gpsd.connect()
    except:
        click.echo("Could not connect to GPSD.")

    try:
        current = gpsd.get_current()
        position = current.position()
        speed = current.speed()
        altitude = current.alt
    except Exception as e:
        click.echo("Unable to get location: {0}".format(e))

    return current

def get_address(gps_location):
    address = None

    try:
        geolocator = Nominatim(user_agent="Sherlock")
        address = geolocator.reverse("{0}, {1}".format(current.lat,
                                                       current.long))
    except Exception as e:
        click.echo("Could not reverse address: {0}".format(e))

    return address

if __name__ == "__main__":
    cli()
