import os
import requests
import time
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional
from pydantic import BaseModel

router = APIRouter()

# Simple In-memory Cache: {city: (data, timestamp)}
weather_cache: Dict[str, tuple] = {}
CACHE_DURATION = 600 # 10 minutes

class WeatherResponse(BaseModel):
    city: str
    temp: float
    description: str
    icon: str
    humidity: int
    wind_speed: float

@router.get("/current")
async def get_current_weather(q: str = Query(..., description="City name, e.g., Nairobi,KE")):
    """Proxy endpoint for OpenWeather API to keep API Key secure on the server."""
    
    # 1. Check Cache
    current_time = time.time()
    if q in weather_cache:
        data, timestamp = weather_cache[q]
        if current_time - timestamp < CACHE_DURATION:
            return data

    # 2. Fetch from OpenWeather
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        # For development, if no key is provided, return a mock response
        return {
            "city": q,
            "temp": 24.5,
            "description": "Partly Cloudy (Demo Mode)",
            "icon": "03d",
            "humidity": 60,
            "wind_speed": 5.1,
            "is_mock": True
        }

    url = f"https://api.openweathermap.org/data/2.5/weather?q={q}&units=metric&appid={api_key}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        raw_data = response.json()
        
        # Transform into a cleaner format
        weather_data = {
            "city": raw_data.get("name", q),
            "temp": raw_data["main"]["temp"],
            "description": raw_data["weather"][0]["description"].capitalize(),
            "icon": raw_data["weather"][0]["icon"],
            "id": raw_data["weather"][0]["id"], # Add ID for icon mapping
            "humidity": raw_data["main"]["humidity"],
            "wind_speed": raw_data["wind"]["speed"]
        }
        
        # Update Cache
        weather_cache[q] = (weather_data, current_time)
        return weather_data

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"OpenWeather API Error: {str(e)}")
    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail="Unexpected response format from Weather API")

@router.get("/batch")
async def get_batch_weather(cities: str = Query("Nairobi,KE;Mombasa,KE;Kisumu,KE", description="Semicolon separated cities")):
    """Fetch weather for multiple cities in one call (useful for the header/sidebar)."""
    city_list = cities.split(";")
    results = []
    for city in city_list:
        try:
            data = await get_current_weather(q=city.strip())
            results.append(data)
        except:
            continue
    return results
