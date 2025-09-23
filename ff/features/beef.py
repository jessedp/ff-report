__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Dict

import requests

from .base import BaseFeature
from ..utils.constants import nfl_team_abbreviation_conversions, nfl_team_abbreviations
from ..utils.utils import generate_normalized_player_key

logger = logging.getLogger(__name__)


class BeefFeature(BaseFeature):
    def __init__(
        self,
        data_dir: Path,
        refresh: bool = False,
        save_data: bool = True,
        offline: bool = False,
    ):
        """Initialize class, load data from Sleeper API, and combine defensive player data into team total"""
        self.tabbu_value: float = 500.0

        defense = {
            "CB": "D",
            "DB": "D",
            "DE": "D",
            "DL": "D",
            "DT": "D",
            "FS": "D",
            "ILB": "D",
            "LB": "D",
            "NT": "D",
            "OLB": "D",
            "S": "D",
            "SS": "D",
        }
        offense = {
            "FB": "O",
            "QB": "O",
            "RB": "O",
            "TE": "O",
            "WR": "O",
        }
        special_teams = {
            "K": "S",
            "K/P": "S",
            "P": "S",
        }
        offensive_line = {
            "C": "L",
            "G": "L",
            "LS": "L",
            "OG": "L",
            "OL": "L",
            "OT": "L",
            "T": "L",
        }
        team_defense = {
            "DEF": "D",
        }
        # position type reference
        self.position_types: Dict[str, str] = {
            **defense,
            **offense,
            **special_teams,
            **offensive_line,
            **team_defense,
        }

        super().__init__(
            "beef",
            "https://api.sleeper.app/v1/players/nfl",
            data_dir,
            False,
            refresh,
            save_data,
            offline,
        )

    def _get_feature_data(self):
        logger.debug("Retrieving beef feature data from the web.")

        nfl_player_data = requests.get(self.feature_web_base_url).json()
        for player_sleeper_key, player_data_json in nfl_player_data.items():
            player_full_name = player_data_json.get("full_name", "")
            player_team_abbr = player_data_json.get("team")
            player_position = player_data_json.get("position")
            player_position_type = self.position_types.get(player_position)

            if player_team_abbr not in nfl_team_abbreviations:
                if player_team_abbr in nfl_team_abbreviation_conversions.keys():
                    player_team_abbr = nfl_team_abbreviation_conversions[
                        player_team_abbr
                    ]
                else:
                    player_team_abbr = "?"

            if player_position == "DEF":
                normalized_player_key = player_position
            else:
                normalized_player_key = generate_normalized_player_key(
                    player_full_name, player_team_abbr
                )

            # add raw player data json to raw_player_data for reference
            self.raw_feature_data[normalized_player_key] = player_data_json

            if player_position != "DEF":
                player_weight = (
                    int(player_data_json.get("weight"))
                    if player_data_json.get("weight")
                    else 0
                )
                player_tabbu = player_weight / float(self.tabbu_value)

                # this looks like this `6'2"`
                player_height = (
                    player_data_json.get("height")
                    if player_data_json.get("height")
                    else ""
                )
                # Convert height from format like "72" (inches) or "6'2" (fheighteet'inches) to total inches

                player_height_inches = 0
                if player_height:
                    if "'" in player_height:
                        # Format like "6'2" - split by apostrophe and convert
                        parts = player_height.split("'")
                        parts[1] = parts[1].strip('"')
                        if len(parts) == 2:
                            feet = int(parts[0]) if parts[0].isdigit() else 0
                            inches = int(parts[1]) if parts[1].isdigit() else 0
                            player_height_inches = feet * 12 + inches
                    else:
                        # Assume it's already in inches
                        player_height_inches = (
                            int(player_height) if player_height.isdigit() else 0
                        )

                        # Convert back to feet'inches" format for display
                        if player_height_inches > 0:
                            feet = player_height_inches // 12
                            inches = player_height_inches % 12
                            player_height = f"{feet}'{inches}\""

                player_years_exp = (
                    int(player_data_json.get("years_exp"))
                    if player_data_json.get("years_exp")
                    else 0
                )
                player_age = (
                    int(player_data_json.get("age"))
                    if player_data_json.get("age")
                    else 0
                )
                player_birth_date = (
                    player_data_json.get("birth_date")
                    if player_data_json.get("birth_date")
                    else ""
                )

                player_beef_dict = {
                    **self._get_feature_data_template(
                        player_full_name,
                        player_team_abbr,
                        player_position,
                        player_position_type,
                    ),
                    "height": player_height,
                    "height_inches": player_height_inches,
                    "weight": player_weight,
                    "tabbu": player_tabbu,
                    "years_exp": player_years_exp,
                    "age": player_age,
                    "birth_date": player_birth_date,
                }

                if normalized_player_key not in self.feature_data.keys():
                    self.feature_data[normalized_player_key] = player_beef_dict

                position_types = player_data_json.get("fantasy_positions")
                if (
                    player_team_abbr != "?"
                    and position_types
                    and ("DL" in position_types or "DB" in position_types)
                ):
                    if player_team_abbr not in self.feature_data.keys():
                        self.feature_data[player_team_abbr] = {
                            "position": "D/ST",
                            "players": {normalized_player_key: player_beef_dict},
                            "weight": player_weight,
                            "tabbu": player_tabbu,
                        }
                    else:
                        self.feature_data[player_team_abbr]["players"][
                            normalized_player_key
                        ] = player_beef_dict
                        self.feature_data[player_team_abbr]["weight"] += player_weight
                        self.feature_data[player_team_abbr]["tabbu"] += player_tabbu

    def get_player_weight(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name,
            player_last_name,
            player_team_abbr,
            player_position,
            "weight",
            int,
        )

    def get_player_tabbu(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> float:
        return round(
            self._get_player_feature_stats(
                player_first_name,
                player_last_name,
                player_team_abbr,
                player_position,
                "tabbu",
                float,
            ),
            3,
        )

    def get_player_height(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> str:
        return self._get_player_feature_stats(
            player_first_name,
            player_last_name,
            player_team_abbr,
            player_position,
            "height",
            str,
        )

    def get_player_height_inches(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name,
            player_last_name,
            player_team_abbr,
            player_position,
            "height_inches",
            int,
        )

    def get_player_years_exp(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name,
            player_last_name,
            player_team_abbr,
            player_position,
            "years_exp",
            int,
        )

    def get_player_age(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name,
            player_last_name,
            player_team_abbr,
            player_position,
            "age",
            int,
        )

    def get_player_birth_date(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name,
            player_last_name,
            player_team_abbr,
            player_position,
            "birth_date",
            int,
        )

    def generate_player_info_json(self):
        ordered_player_data = OrderedDict(
            sorted(self.raw_feature_data.items(), key=lambda k_v: k_v[0])
        )
        with open(
            self.data_dir / f"{self.feature_type_str}_raw.json",
            mode="w",
            encoding="utf-8",
        ) as player_data:
            # noinspection PyTypeChecker
            json.dump(ordered_player_data, player_data, ensure_ascii=False, indent=2)
