import gpsd

import click


@click.group(invoke_without_command=True)
def cli():
    current = None

    try:
        gpsd.connect()
    except UserWarning as e:
        click.echo(e)
        return
    except Exception as e:
        click.echo(e)
        return

    try:
        current = gpsd.get_current()
        position = current.position()
    except Exception as e:
        click.echo(e)
        return

    if current and current.mode > 1:
        click.echo("GPS functioning nominally.")
    else:
        click.echo("Unable to acquire fix.")

    return current

if __name__ == "__main__":
    cli()
