__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Type, Union
import os

from ..utils.constants import nfl_team_abbreviation_conversions, nfl_team_abbreviations
from ..utils.utils import FFMWRPythonObjectJson, generate_normalized_player_key

logger = logging.getLogger(__name__)


class BaseFeature(ABC, FFMWRPythonObjectJson):
    def __init__(
        self,
        feature_type: str,
        feature_web_base_url: str,
        data_dir: Path,
        exclude_dst: bool = False,
        refresh: bool = False,
        save_data: bool = True,
        offline: bool = False,
    ):
        """Base Feature class for retrieving data from tb web, saving, and loading it."""
        super().__init__()
        self.excluded_attributes.append("raw_feature_data")

        self.feature_type_str: str = feature_type.replace(" ", "_").lower()
        self.feature_type_title: str = feature_type.replace("_", " ").title()

        logger.debug(f"Initializing {self.feature_type_title} feature.")

        self.feature_web_base_url = feature_web_base_url

        self.data_dir: Path = data_dir
        self.feature_data_file_path: Path = (
            self.data_dir / f"{self.feature_type_str}.json"
        )
        os.makedirs(self.data_dir, exist_ok=True)

        self.refresh: bool = refresh
        self.save_data: bool = save_data
        self.offline: bool = offline

        self.exclude_dst: bool = exclude_dst

        self.raw_feature_data: Dict[str, Any] = {}
        self.feature_data: Dict[str, Any] = {}

        start = datetime.now()

        # Caching logic
        data_retrieved_from_web = False
        if not self.offline:
            should_refresh = self.refresh
            if not should_refresh and self.feature_data_file_path.is_file():
                # Check file age for daily caching
                file_mod_time = datetime.fromtimestamp(
                    self.feature_data_file_path.stat().st_mtime
                )
                if datetime.now() - file_mod_time > timedelta(days=1):
                    should_refresh = True

            if not self.feature_data_file_path.is_file() or should_refresh:
                logger.info(
                    f"Retrieving {self.feature_type_title} data from {self.feature_web_base_url}..."
                )
                # fetch feature data from the web
                self._get_feature_data()
                data_retrieved_from_web = True

                if self.save_data:
                    self._save_feature_data()
            else:
                # load saved feature data
                self._load_feature_data()
        else:
            # load saved feature data
            self._load_feature_data()

        if len(self.feature_data) == 0:
            logger.warning(
                f"...{'retrieved' if data_retrieved_from_web else 'loaded'} 0 {self.feature_type_title} data records. "
                f"Please check your internet connection or the availability of {self.feature_web_base_url} and try "
                f"generating a new report."
            )
        else:
            logger.info(
                f"...{'retrieved' if data_retrieved_from_web else 'loaded'} {len(self.feature_data)} "
                f"{self.feature_type_title} data records in {datetime.now() - start}."
            )

    def __str__(self):
        return json.dumps(self.feature_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.feature_data, indent=2, ensure_ascii=False)

    def _load_feature_data(self) -> None:
        logger.info(f"Loading saved {self.feature_type_title} data...")

        try:
            self.load_from_json_file(self.feature_data_file_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"FILE {self.feature_data_file_path} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY "
                f"SAVED DATA!"
            ) from e

    def _save_feature_data(self) -> None:
        logger.debug(f"Saving {self.feature_type_title} data...")

        if self.save_data:
            self.save_to_json_file(self.feature_data_file_path)

    def _get_player_feature_stats(
        self,
        player_first_name: str,
        player_last_name: str,
        player_team_abbr: str,
        player_position: str,
        key_str: str,
        key_type: Type,
    ) -> Union[int, float, str]:
        player_full_name = (
            f"{player_first_name.title() if player_first_name else ''}"
            f"{' ' if player_first_name and player_last_name else ''}"
            f"{player_last_name.title() if player_last_name else ''}"
        ).strip()
        player_team_abbr = player_team_abbr.upper() if player_team_abbr else "?"

        if player_team_abbr not in nfl_team_abbreviations:
            if player_team_abbr in nfl_team_abbreviation_conversions.keys():
                player_team_abbr = nfl_team_abbreviation_conversions[player_team_abbr]

        # set feature data access key to NFL team abbreviation if player is D/ST
        if player_position == "D/ST":
            # skip inclusion of rolled up D/ST for feature if exclude_dst is True
            if self.exclude_dst:
                normalized_player_key = None
            else:
                normalized_player_key = player_team_abbr
        else:
            normalized_player_key = generate_normalized_player_key(
                player_full_name, player_team_abbr
            )

        if normalized_player_key in self.feature_data:
            return self.feature_data[normalized_player_key].get(key_str, key_type())
        else:
            # Only print debug info for beef feature failures
            if self.feature_type_str == "beef":
                print(f"DEBUG: BEEF MISMATCH for player '{player_full_name}'")
                print(f"  -> Generated Key: '{normalized_player_key}'")
                if player_last_name:
                    potential_matches = [
                        k
                        for k in self.feature_data.keys()
                        if player_last_name.lower() in k
                    ]
                    if potential_matches:
                        print(
                            f"  -> Potential matches in beef data for '{player_last_name}': {potential_matches[:5]}"
                        )
                    else:
                        print(
                            f"  -> No potential matches found for last name '{player_last_name}'."
                        )
            return key_type()

    @staticmethod
    def _get_feature_data_template(
        player_full_name: str,
        player_team_abbr: str,
        player_position: str,
        player_position_type: str,
    ) -> Dict[str, Any]:
        return {
            "full_name": player_full_name,
            "team_abbr": player_team_abbr,
            "position": player_position,
            "position_type": player_position_type,
        }

    @abstractmethod
    def _get_feature_data(self) -> None:
        raise NotImplementedError
