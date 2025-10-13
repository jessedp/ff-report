import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import BaseFeature

logger = logging.getLogger(__name__)


class AttendanceFeature(BaseFeature):
    def __init__(
        self,
        data_dir: Path,
        refresh: bool = False,
        save_data: bool = True,
        offline: bool = False,
        week: Optional[int] = None,
    ):
        self.week = week
        super().__init__(
            feature_type="attendance",
            feature_web_base_url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            data_dir=data_dir,
            refresh=refresh,
            save_data=save_data,
            offline=offline,
        )

    def _get_feature_data(self) -> None:
        scoreboard_url = f"{self.feature_web_base_url}?week={self.week}"
        logger.debug(f"Fetching scoreboard data from: {scoreboard_url}")

        try:
            scoreboard_response = requests.get(scoreboard_url)
            scoreboard_response.raise_for_status()
            scoreboard_data = scoreboard_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching scoreboard data for week {self.week}: {e}")
            return

        self.feature_data = [] # Store a list of game events
        for event in scoreboard_data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            
            game_date = competition.get("date")
            attendance = competition.get("attendance")
            
            venue_address = competition.get("venue", {}).get("address", {})
            city = venue_address.get("city")
            state = venue_address.get("state")
            country = venue_address.get("country")

            # Extract team abbreviations from shortName (e.g., "GB @ CLE")
            short_name = event.get("shortName")
            home_team_abbrev = None
            away_team_abbrev = None
            if short_name:
                match = re.match(r"(\w+) @ (\w+)", short_name)
                if match:
                    away_team_abbrev = match.group(1)
                    home_team_abbrev = match.group(2)

            if all([game_date, attendance, city, state, country, home_team_abbrev, away_team_abbrev]):
                self.feature_data.append({
                    "date": game_date,
                    "attendance": attendance,
                    "city": city,
                    "state": state,
                    "country": country,
                    "home_team_abbrev": home_team_abbrev,
                    "away_team_abbrev": away_team_abbrev
                })
