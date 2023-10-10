from typing import Optional

from fastapi import FastAPI

from pydantic import BaseModel


class Location(BaseModel):
    mode: int
    alt: Optional[int]
    track: Optional[int]
    speed: Optional[float]
    lat: Optional[float]
    lon: Optional[float]


app = FastAPI()
app.current_location = None


@app.get("/location")
async def location():
    return app.current_location


@app.put("/location")
async def create_location(location: Location):
    app.current_location = location

    return app.current_location
