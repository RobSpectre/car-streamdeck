import json

import click

import requests

from gpsdclient import GPSDClient


@click.group(invoke_without_command=True)
@click.pass_context
def cli(context):
    with GPSDClient() as client:
        for result in client.json_stream(filter=["TPV"]):
            click.echo(result)

            result = json.loads(result)

            coordinates = {
                "mode": result.get("mode", 0),
                "alt": result.get("alt", 0),
                "track": result.get("track", 0),
                "speed": result.get("speed", 0),
                "lat": result.get("lat", 0),
                "lon": result.get("lon", 0)
            }

            try:
                requests.put('http://localhost:8000/location',
                             json=coordinates)
            except Exception as e:
                click.echo(f"Error: {e}")


if __name__ == "__main__":
    cli()
