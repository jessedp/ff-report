from geopy.geocoders import Nominatim
from geopy.location import Location
import json
from pathlib import Path
import requests
import logging

logger = logging.getLogger(__name__)


class Geocoder:
    def __init__(
        self,
        user_agent="fantasy-football-report",
        cache_dir="cache/geocoding",
        timeout=10,
    ):
        self.geolocator = Nominatim(user_agent=user_agent, timeout=timeout)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.forward_cache_file = self.cache_dir / "forward_cache.json"
        self.reverse_cache_file = self.cache_dir / "reverse_cache.json"
        self.stadium_cache_file = self.cache_dir / "stadium_cache.json"
        self.forward_cache = self._load_cache(self.forward_cache_file)
        self.reverse_cache = self._load_cache(self.reverse_cache_file)
        self.stadium_cache = self._load_cache(self.stadium_cache_file)

    def _load_cache(self, cache_file: Path) -> dict:
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cache(self, cache: dict, cache_file: Path):
        with open(cache_file, "w") as f:
            json.dump(cache, f)

    def geocode(self, address: str) -> Location:
        """Forward geocoding (address -> lat/lon)"""
        if address in self.forward_cache:
            logger.debug(f"Geocode cache hit for address: {address}")
            cached_data = self.forward_cache[address]
            return Location(
                cached_data["address"],
                (cached_data["latitude"], cached_data["longitude"]),
                cached_data["raw"],
            )

        logger.info(f"Geocoding address: {address}")
        location = self.geolocator.geocode(address)
        if location:
            logger.info(
                f"Geocoded {address} to {location.latitude}, {location.longitude}"
            )
            self.forward_cache[address] = {
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "raw": location.raw,  # Store raw data for full reconstruction
            }
            self._save_cache(self.forward_cache, self.forward_cache_file)
        else:
            logger.warning(f"Could not geocode address: {address}")
        return location

    def reverse_geocode(
        self, latitude: float, longitude: float, language="en"
    ) -> Location:
        """Reverse geocoding (lat/lon -> address)"""
        key = f"{latitude},{longitude},{language}"
        if key in self.reverse_cache:
            logger.debug(f"Reverse geocode cache hit for key: {key}")
            cached_data = self.reverse_cache[key]
            return Location(
                cached_data["address"],
                (cached_data["latitude"], cached_data["longitude"]),
                cached_data["raw"],
            )

        logger.info(f"Reverse geocoding coordinates: {latitude}, {longitude}")
        location = self.geolocator.reverse((latitude, longitude), language=language)
        if location:
            logger.info(
                f"Reverse geocoded {latitude}, {longitude} to {location.address}"
            )
            self.reverse_cache[key] = {
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "raw": location.raw,
            }
            self._save_cache(self.reverse_cache, self.reverse_cache_file)
        else:
            logger.warning(
                f"Could not reverse geocode coordinates: {latitude}, {longitude}"
            )
        return location

    def find_nearby_stadiums(
        self, latitude: float, longitude: float, radius: int = 100000
    ) -> list:
        """Finds football stadiums near a given latitude and longitude using Overpass API."""
        key = f"{latitude},{longitude},{radius}"
        if key in self.stadium_cache:
            logger.debug(f"Stadium cache hit for key: {key}")
            return self.stadium_cache[key]

        logger.info(
            f"Searching for stadiums around {latitude}, {longitude} with radius {radius}"
        )
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
[out:json];
(
  node["leisure"="stadium"](around:{radius},{latitude},{longitude});
  way["leisure"="stadium"](around:{radius},{latitude},{longitude});
  relation["leisure"="stadium"](around:{radius},{latitude},{longitude});
);
out center;
"""
        logger.info(query)

        stadiums = []
        try:
            response = requests.get(overpass_url, params={"data": query})
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            print(json.dumps(data, indent=4))
            for element in data["elements"]:
                name = element["tags"].get("name", "Unnamed Stadium")
                stadium_lat = (
                    element["lat"]
                    if element["type"] == "node"
                    else element["center"]["lat"]
                )
                stadium_lon = (
                    element["lon"]
                    if element["type"] == "node"
                    else element["center"]["lon"]
                )
                stadiums.append({"name": name, "lat": stadium_lat, "lon": stadium_lon})
            logger.info(f"Found {len(stadiums)} stadiums: {[s['name'] for s in stadiums]}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Overpass API: {e}")
        except json.JSONDecodeError:
            logger.error("Error decoding JSON response from Overpass API.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while finding stadiums: {e}")

        if stadiums: # Only cache if stadiums are found
            self.stadium_cache[key] = stadiums
            self._save_cache(self.stadium_cache, self.stadium_cache_file)
        return stadiums
