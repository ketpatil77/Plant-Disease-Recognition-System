from __future__ import annotations

import json
import time
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from statistics import mean
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ATTRIBUTION_URL = "https://open-meteo.com/"
REQUEST_TIMEOUT_SECONDS = 8
CACHE_TTL_SECONDS = 600
CACHE_PRECISION = 2
WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}
WEATHER_CACHE_LOCK = Lock()


class WeatherServiceError(RuntimeError):
    """Raised when live weather data cannot be fetched or normalized."""


def get_live_weather(latitude: float, longitude: float) -> dict:
    lat, lon = normalize_coordinates(latitude, longitude)
    cache_key = (round(lat, CACHE_PRECISION), round(lon, CACHE_PRECISION))

    cached_payload = get_cached_weather(cache_key)
    if cached_payload is not None:
        cached_payload["cached"] = True
        return cached_payload

    raw_payload = fetch_open_meteo_weather(lat, lon)
    weather_payload = build_weather_payload(lat, lon, raw_payload)
    set_cached_weather(cache_key, weather_payload)
    weather_payload["cached"] = False
    return weather_payload


def normalize_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError("अक्षांश आणि रेखांश वैध संख्यांमध्ये द्या.") from exc

    if not -90 <= lat <= 90:
        raise ValueError("अक्षांश -90 ते 90 दरम्यान असावा.")
    if not -180 <= lon <= 180:
        raise ValueError("रेखांश -180 ते 180 दरम्यान असावा.")
    return lat, lon


def get_cached_weather(cache_key: tuple[float, float]) -> dict | None:
    now = time.time()
    with WEATHER_CACHE_LOCK:
        cached_entry = WEATHER_CACHE.get(cache_key)
        if not cached_entry:
            return None
        cached_at, payload = cached_entry
        if now - cached_at > CACHE_TTL_SECONDS:
            WEATHER_CACHE.pop(cache_key, None)
            return None
        return deepcopy(payload)


def set_cached_weather(cache_key: tuple[float, float], payload: dict) -> None:
    with WEATHER_CACHE_LOCK:
        WEATHER_CACHE[cache_key] = (time.time(), deepcopy(payload))


def fetch_open_meteo_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": f"{latitude:.6f}",
        "longitude": f"{longitude:.6f}",
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "rain",
                "weather_code",
                "wind_speed_10m",
                "is_day",
            ]
        ),
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "precipitation_probability",
                "rain",
                "wind_speed_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "wind_speed_10m_max",
            ]
        ),
        "forecast_days": 3,
        "timezone": "auto",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    request = Request(
        f"{OPEN_METEO_FORECAST_URL}?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "User-Agent": "AgroVision/1.0 (local dashboard weather integration)",
        },
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except HTTPError as exc:
        raise WeatherServiceError(f"हवामान सेवा HTTP {exc.code} त्रुटी परत करत आहे.") from exc
    except URLError as exc:
        raise WeatherServiceError("हवामान सेवा सध्या उपलब्ध नाही.") from exc
    except json.JSONDecodeError as exc:
        raise WeatherServiceError("हवामान सेवेकडून अवैध माहिती मिळाली.") from exc


def build_weather_payload(latitude: float, longitude: float, payload: dict) -> dict:
    current = payload.get("current") or {}
    hourly = payload.get("hourly") or {}
    daily = payload.get("daily") or {}
    daily_times = daily.get("time") or []
    hourly_by_day = group_hourly_by_day(hourly)

    next_12_hours = slice_hourly(hourly, 12)
    next_24_hours = slice_hourly(hourly, 24)

    current_temperature = number_or_zero(current.get("temperature_2m"))
    current_humidity = number_or_zero(current.get("relative_humidity_2m"))
    current_wind = round(number_or_zero(current.get("wind_speed_10m")))
    next_12_humidity = average_or_default(next_12_hours.get("relative_humidity_2m"), current_humidity)
    next_12_rain_chance = round(max_or_default(next_12_hours.get("precipitation_probability"), 0.0))
    next_24_rain = round(sum_or_zero(next_24_hours.get("precipitation")), 1)
    current_level, current_score = score_disease_pressure(
        temperature=current_temperature,
        humidity=next_12_humidity,
        rain_chance=next_12_rain_chance,
        rain_mm=next_24_rain,
        wind_speed=current_wind,
    )

    forecast = []
    for index, day_key in enumerate(daily_times[:3]):
        daily_bucket = hourly_by_day.get(day_key, {})
        daily_temp_max = number_or_zero(value_at(daily.get("temperature_2m_max"), index))
        daily_temp_min = number_or_zero(value_at(daily.get("temperature_2m_min"), index))
        daily_temperature = average_or_default(
            daily_bucket.get("temperature_2m"),
            (daily_temp_max + daily_temp_min) / 2,
        )
        daily_humidity = round(
            average_or_default(
                daily_bucket.get("relative_humidity_2m"),
                current_humidity,
            )
        )
        daily_rain_mm = round(
            number_or_zero(value_at(daily.get("precipitation_sum"), index)) or sum_or_zero(daily_bucket.get("precipitation")),
            1,
        )
        daily_rain_chance = round(
            number_or_zero(value_at(daily.get("precipitation_probability_max"), index))
            or max_or_default(daily_bucket.get("precipitation_probability"), 0.0)
        )
        daily_wind = round(
            number_or_zero(value_at(daily.get("wind_speed_10m_max"), index))
            or max_or_default(daily_bucket.get("wind_speed_10m"), current_wind)
        )
        level, score = score_disease_pressure(
            temperature=daily_temperature,
            humidity=daily_humidity,
            rain_chance=daily_rain_chance,
            rain_mm=daily_rain_mm,
            wind_speed=daily_wind,
        )
        weather_code = int(number_or_zero(value_at(daily.get("weather_code"), index)))
        forecast.append(
            {
                "day": forecast_day_label(day_key, index),
                "date": day_key,
                "level": level,
                "risk_score": score,
                "temperature": round(daily_temperature),
                "humidity": daily_humidity,
                "rain_chance": daily_rain_chance,
                "rain_mm": daily_rain_mm,
                "icon": weather_icon(weather_code, is_day=True),
                "description": forecast_description(
                    level=level,
                    temperature=daily_temperature,
                    humidity=daily_humidity,
                    rain_chance=daily_rain_chance,
                    rain_mm=daily_rain_mm,
                ),
            }
        )

    condition_code = int(number_or_zero(current.get("weather_code")))
    is_day = bool(number_or_zero(current.get("is_day")))

    return {
        "source": "open-meteo",
        "source_url": OPEN_METEO_ATTRIBUTION_URL,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "location": {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "label": f"{latitude:.4f}, {longitude:.4f}",
            "timezone": payload.get("timezone") or "auto",
        },
        "current": {
            "temperature": round(current_temperature),
            "humidity": round(current_humidity),
            "rain_mm_24h": next_24_rain,
            "rain_chance": next_12_rain_chance,
            "wind_speed": current_wind,
            "apparent_temperature": round(number_or_zero(current.get("apparent_temperature"))),
            "condition_code": condition_code,
            "condition_icon": weather_icon(condition_code, is_day=is_day),
            "risk": current_level,
            "risk_score": current_score,
            "tip": current_tip(
                level=current_level,
                temperature=current_temperature,
                humidity=current_humidity,
                rain_chance=next_12_rain_chance,
            ),
            "summary": current_summary(
                level=current_level,
                rain_chance=next_12_rain_chance,
                rain_mm=next_24_rain,
            ),
            "observed_at": current.get("time"),
        },
        "forecast": forecast,
    }


def group_hourly_by_day(hourly: dict) -> dict[str, dict[str, list[float]]]:
    tracked_keys = (
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "precipitation_probability",
        "rain",
        "wind_speed_10m",
    )
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    times = hourly.get("time") or []

    for index, timestamp in enumerate(times[:72]):
        day_key = timestamp[:10]
        bucket = grouped[day_key]
        for key in tracked_keys:
            values = hourly.get(key) or []
            if index >= len(values):
                continue
            value = values[index]
            if value is None:
                continue
            bucket[key].append(float(value))
    return {day: dict(values) for day, values in grouped.items()}


def slice_hourly(hourly: dict, hour_count: int) -> dict[str, list[float]]:
    tracked_keys = (
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "precipitation_probability",
        "rain",
        "wind_speed_10m",
    )
    sliced: dict[str, list[float]] = {}
    for key in tracked_keys:
        values = hourly.get(key) or []
        sliced[key] = [float(value) for value in values[:hour_count] if value is not None]
    return sliced


def score_disease_pressure(
    *,
    temperature: float,
    humidity: float,
    rain_chance: float,
    rain_mm: float,
    wind_speed: float,
) -> tuple[str, int]:
    score = 10.0

    if 18 <= temperature <= 28:
        score += 18
    elif 12 <= temperature < 18 or 28 < temperature <= 32:
        score += 10
    elif temperature > 35:
        score -= 8

    if humidity >= 90:
        score += 30
    elif humidity >= 80:
        score += 22
    elif humidity >= 70:
        score += 14
    elif humidity >= 60:
        score += 6

    if rain_chance >= 80:
        score += 18
    elif rain_chance >= 55:
        score += 12
    elif rain_chance >= 30:
        score += 6

    if rain_mm >= 10:
        score += 18
    elif rain_mm >= 4:
        score += 12
    elif rain_mm >= 1:
        score += 6

    if wind_speed <= 12 and humidity >= 80:
        score += 6
    elif wind_speed >= 28 and humidity < 60:
        score -= 5

    bounded_score = max(0, min(100, round(score)))
    if bounded_score >= 67:
        return "high", bounded_score
    if bounded_score >= 40:
        return "medium", bounded_score
    return "low", bounded_score


def current_tip(*, level: str, temperature: float, humidity: float, rain_chance: float) -> str:
    if temperature >= 34 and humidity < 50:
        return "रोगदाबापेक्षा उष्णताजन्य ताण अधिक वाढत आहे. सकाळी लवकर सिंचन करा आणि पाहणी सुरू ठेवा."
    if level == "high":
        return "ओलाव्याचा कालावधी जास्त आहे. सूर्योदयाच्या वेळी पाहणी करा, हवाप्रवाह वाढवा आणि संध्याकाळी सिंचन टाळा."
    if level == "medium":
        return "आर्द्रता रोगाला पोषक आहे. पावसाच्या आधी आणि नंतर दाट छत्री असलेल्या पट्ट्यांची तपासणी करा."
    if rain_chance >= 40:
        return "पावसाची शक्यता वाढत आहे. पुढील ओलसर कालावधीनंतर खालची पाने तपासा."
    return "सध्या रोगदाब कमी आहे. नियमित पाहणी ठेवा आणि अनियमित पाणी देणे टाळा."


def current_summary(*, level: str, rain_chance: float, rain_mm: float) -> str:
    if level == "high":
        return "दमट आणि ओलसर हवामानामुळे पानांवरील रोग जलद पसरू शकतात."
    if level == "medium":
        return "हवामान मिश्र आहे. पुढील ओलसर कालावधीपूर्वी संवेदनशील पट्ट्यांवर लक्ष ठेवा."
    if rain_mm >= 3 or rain_chance >= 45:
        return "सध्या रोगदाब मर्यादित आहे, पण येणाऱ्या सरींमुळे परिस्थिती लगेच बदलू शकते."
    return "कोरड्या हवेमुळे सध्याचा रोगदाब कमी राहतो आहे."


def forecast_description(*, level: str, temperature: float, humidity: float, rain_chance: float, rain_mm: float) -> str:
    if level == "high":
        return f"आर्द्रता सुमारे {humidity:.0f}% आणि पावसाची {rain_chance:.0f}% शक्यता असल्याने पानांवरील रोगदाब वाढलेला राहू शकतो."
    if level == "medium":
        return f"ओलाव्याचे संकेत मिश्र आहेत. पाऊस {rain_mm:.1f} मिमीपर्यंत गेला तर दाट ओळींवर विशेष लक्ष ठेवा."
    if temperature >= 33 and humidity < 55:
        return "उष्ण आणि कोरड्या हवेमुळे पानावरील रोग कमी राहू शकतात, पण पिकावरील ताण वाढू शकतो."
    return "कोरड्या स्थितीत रोग प्रसार मंदावू शकतो, तरी नियमित पाहणी महत्त्वाची आहे."


def forecast_day_label(day_key: str, index: int) -> str:
    if index == 0:
        return "आज"
    if index == 1:
        return "उद्या"
    try:
        return {
            "Mon": "सोम",
            "Tue": "मंगळ",
            "Wed": "बुध",
            "Thu": "गुरु",
            "Fri": "शुक्र",
            "Sat": "शनि",
            "Sun": "रवि",
        }.get(datetime.fromisoformat(day_key).strftime("%a"), f"दिवस {index + 1}")
    except ValueError:
        return f"दिवस {index + 1}"


def weather_icon(weather_code: int, *, is_day: bool) -> str:
    if weather_code == 0:
        return "☀️" if is_day else "🌙"
    if weather_code in {1, 2}:
        return "🌤️" if is_day else "☁️"
    if weather_code == 3:
        return "☁️"
    if weather_code in {45, 48}:
        return "🌫️"
    if weather_code in {51, 53, 55, 56, 57}:
        return "🌦️"
    if weather_code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "🌧️"
    if weather_code in {71, 73, 75, 77, 85, 86}:
        return "❄️"
    if weather_code in {95, 96, 99}:
        return "⛈️"
    return "🌥️"


def value_at(values: list | None, index: int):
    if not values or index >= len(values):
        return None
    return values[index]


def number_or_zero(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def average_or_default(values: list[float] | None, default: float) -> float:
    if not values:
        return float(default)
    return float(mean(values))


def max_or_default(values: list[float] | None, default: float) -> float:
    if not values:
        return float(default)
    return float(max(values))


def sum_or_zero(values: list[float] | None) -> float:
    if not values:
        return 0.0
    return float(sum(values))
