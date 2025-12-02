"""Generate fantasy football reports"""

from asyncio import sleep
import os
import hashlib
import urllib.request
import shutil
from datetime import timedelta, datetime
from pathlib import Path
import json
from .data import LeagueData
from .stat_category_map import STAT_CATEGORY_LOOKUP
from espn_api.football.constant import SETTINGS_SCORING_FORMAT_MAP, PLAYER_STATS_MAP
from .stats import (
    calculate_weekly_scores,
    calculate_matchups,
    points_per_player_per_position,
    calculate_top_players,
)
from .templates import TemplateEngine
from .config import LEAGUE_YEAR, SWID, ESPN_S2
from .features.beef import BeefFeature
from .features.high_roller import HighRollerFeature
from .features.attendance import AttendanceFeature
from .utils.geocoding_utils import Geocoder


def cache_logo(logo_url):
    """Downloads and caches a logo if not already present.

    Args:
        logo_url: The URL of the logo to download.

    Returns:
        The local filename of the cached logo.
    """
    if not logo_url:
        return None

    if not logo_url.startswith("http"):
        filename = os.path.basename(logo_url)
        cache_dir = "cache/images"
        os.makedirs(cache_dir, exist_ok=True)
        local_path = os.path.join(cache_dir, filename)
        if not os.path.exists(local_path):
            shutil.copy(logo_url, local_path)
        return filename

    # Store the original URL for hashing
    original_logo_url = logo_url

    # Handle specific URL redirects
    if (
        "https://practicalhorsemanmag.com/.image/t_share/MTQ0ODEwNTE0ODI5MDI2Njc4/ph-acorns-horses.png"
        in logo_url
    ):
        # print("[WARN] Downloading replacement logo")
        # This is the URL we *want* to download if the original matches the pattern
        logo_url_to_download = f"https://practicalhorsemanmag.com/wp-content/uploads/migrations/practicalhorseman/PH-acorns-horses.png"
    else:
        # For other URLs, we download the original
        logo_url_to_download = logo_url

    # Calculate hash based on the ORIGINAL URL, so all requests for the original URL map to the same cache file
    url_hash = hashlib.md5(original_logo_url.encode("utf-8")).hexdigest()
    file_extension = os.path.splitext(logo_url_to_download)[
        1
    ]  # Use extension from the URL we intend to download
    if "_dark" in file_extension:
        file_extension = file_extension.replace("_dark", "")
    if "?" in file_extension:
        file_extension = file_extension.split("?")[0]
    if not file_extension:
        file_extension = ".png"

    filename = f"{url_hash}{file_extension}"
    cache_dir = "cache/images"
    os.makedirs(cache_dir, exist_ok=True)
    local_path = os.path.join(cache_dir, filename)

    # Download if it doesn't exist
    if not os.path.exists(local_path):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://fantasy.espn.com/",
                "Accept": "*/*",
                "Cookie": f"swid={SWID}; espn_s2={ESPN_S2};",
            }
            req = urllib.request.Request(
                logo_url_to_download, headers=headers
            )  # Use the URL we decided to download
            with (
                urllib.request.urlopen(req) as response,
                open(local_path, "wb") as out_file,
            ):
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(
                f"Error downloading logo: {logo_url_to_download} - {e}"
            )  # Print the URL that failed
            # Fallback to default image
            default_logo_filename = "placeholder.png"
            default_logo_source_path = os.path.join("images", default_logo_filename)

            try:
                shutil.copy(
                    default_logo_source_path, local_path
                )  # Copy to the calculated local_path
                return filename  # Return the calculated filename
            except FileNotFoundError:
                print(
                    f"Default logo not found at {default_logo_source_path}. Returning None."
                )
                return None
            except Exception as copy_e:
                print(f"Error copying default logo to cache: {copy_e}. Returning None.")
                return None

    return filename


class WeeklyReport:
    """Generate weekly fantasy football reports"""

    def __init__(self, year=LEAGUE_YEAR):
        """Initialize the report generator

        Args:
            year: The NFL season year to generate a report for
        """
        self.year = year
        self.data = LeagueData(year)
        self.template = TemplateEngine()
        self.root_dir = Path(__file__).parent.parent

    def get_zodiac_emoji(self, birth_date_str):
        """Get zodiac emoji based on birth date string"""
        if not birth_date_str:
            return ""

        try:
            from datetime import datetime

            # Parse birth date (assuming it could be various formats)
            if isinstance(birth_date_str, int):
                # Convert timestamp to date if it's an integer
                birth_date = (
                    datetime.fromtimestamp(birth_date_str / 1000).date()
                    if birth_date_str > 100000000
                    else datetime.fromtimestamp(birth_date_str).date()
                )
            elif isinstance(birth_date_str, str):
                # Try parsing as YYYY-MM-DD format
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            else:
                return ""

            month = birth_date.month
            day = birth_date.day

            # Zodiac sign calculation based on month and day
            if (month == 3 and day >= 21) or (month == 4 and day <= 19):
                return "♈"  # Aries
            elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
                return "♉"  # Taurus
            elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
                return "♊"  # Gemini
            elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
                return "♋"  # Cancer
            elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
                return "♌"  # Leo
            elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
                return "♍"  # Virgo
            elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
                return "♎"  # Libra
            elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
                return "♏"  # Scorpio
            elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
                return "♐"  # Sagittarius
            elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
                return "♑"  # Capricorn
            elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
                return "♒"  # Aquarius
            elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
                return "♓"  # Pisces
            else:
                return ""
        except (ValueError, TypeError, AttributeError):
            return ""

    def get_zodiac_name(self, zodiac_emoji):
        """Get zodiac name from emoji"""
        zodiac_names = {
            "♈": "Aries",
            "♉": "Taurus",
            "♊": "Gemini",
            "♋": "Cancer",
            "♌": "Leo",
            "♍": "Virgo",
            "♎": "Libra",
            "♏": "Scorpio",
            "♐": "Sagittarius",
            "♑": "Capricorn",
            "♒": "Aquarius",
            "♓": "Pisces",
        }
        return zodiac_names.get(zodiac_emoji, "")

    def _calculate_faked_data(self, game_data_list):
        if not game_data_list:
            return {
                "avg_lat": None,
                "avg_lon": None,
                "avg_attendance": None,
                "avg_timestamp": None,
            }

        total_lat = 0
        total_lon = 0
        total_attendance = 0
        total_timestamp = 0
        valid_entries = 0

        for game_data in game_data_list:
            if (
                game_data["latlng"]
                and game_data["latlng"][0] is not None
                and game_data["latlng"][1] is not None
            ):
                total_lat += game_data["latlng"][0]
                total_lon += game_data["latlng"][1]
            if game_data["attendance"] is not None:
                total_attendance += game_data["attendance"]
            if game_data["date"]:
                # Convert date string to datetime object, then to timestamp
                dt_object = datetime.strptime(game_data["date"], "%Y-%m-%dT%H:%MZ")
                total_timestamp += dt_object.timestamp()
            valid_entries += 1

        if valid_entries == 0:
            return {
                "avg_lat": None,
                "avg_lon": None,
                "avg_attendance": None,
                "avg_timestamp": None,
            }

        avg_lat = total_lat / valid_entries
        avg_lon = total_lon / valid_entries
        avg_attendance = total_attendance / valid_entries
        avg_timestamp = total_timestamp / valid_entries

        return {
            "avg_lat": avg_lat,
            "avg_lon": avg_lon,
            "avg_attendance": avg_attendance,
            "avg_timestamp": avg_timestamp,
        }

    def generate(self, week=None, output_file=None):
        """Generate a weekly report

        Args:
            week: The week number to generate a report for (uses current week if None)
            output_file: The file path to write the report to (auto-generated if None)

        Returns:
            Path to the generated HTML file
        """
        # Determine the week to use
        if week is None:
            week = self.data.get_current_week()

        # Set the week for data retrieval
        self.data.set_week(week)

        # Get all the data for the report
        box_scores = self.data.get_box_scores(week)

        # Determine the Monday date for the current week based on the first game's date
        # Assuming game_date is a datetime object and the first game is representative of the week
        first_game_date = box_scores[0].home_lineup[0].game_date.date()
        # Calculate the Monday of that week (Monday is weekday 0)
        week_monday_date = first_game_date - timedelta(
            days=first_game_date.weekday() - 0
        )
        # Adjust to the Monday *after* the current week
        target_monday_date = week_monday_date + timedelta(days=7)

        matchups = calculate_matchups(box_scores)
        weekly_scores = calculate_weekly_scores(box_scores)

        # Sort weekly scores by score (highest first)
        weekly_scores.sort(key=lambda x: x["score"], reverse=True)

        # --- Margin of Victory ---
        team_abbrev_to_name = {
            team.team_abbrev: team.team_name for team in self.data.league.teams
        }

        largest_weekly_margin = None
        max_weekly_margin = -1

        for matchup in matchups:
            margin = abs(matchup["home_team"]["score"] - matchup["away_team"]["score"])
            if margin > max_weekly_margin:
                max_weekly_margin = margin
                if matchup["winner"] == "home":
                    winner = matchup["home_team"]
                    loser = matchup["away_team"]
                else:
                    winner = matchup["away_team"]
                    loser = matchup["home_team"]

                winner_name = team_abbrev_to_name.get(winner["abbrev"])

                largest_weekly_margin = {
                    "winner_name": winner_name,
                    "winner_score": winner["score"],
                    "loser_score": loser["score"],
                    "margin": margin,
                }

        largest_season_margin = None
        max_season_margin = -1

        for w in range(1, week + 1):
            weekly_box_scores = self.data.get_box_scores(w)
            weekly_matchups = calculate_matchups(weekly_box_scores)
            for matchup in weekly_matchups:
                margin = abs(
                    matchup["home_team"]["score"] - matchup["away_team"]["score"]
                )
                if margin > max_season_margin:
                    max_season_margin = margin
                    if matchup["winner"] == "home":
                        winner = matchup["home_team"]
                        loser = matchup["away_team"]
                    else:
                        winner = matchup["away_team"]
                        loser = matchup["home_team"]

                    winner_name = team_abbrev_to_name.get(winner["abbrev"])

                    largest_season_margin = {
                        "winner_name": winner_name,
                        "winner_score": winner["score"],
                        "loser_score": loser["score"],
                        "margin": margin,
                    }

        # --- Logo Caching ---
        for matchup in matchups:
            if "logo" in matchup["home_team"]:
                matchup["home_team"]["logo"] = cache_logo(matchup["home_team"]["logo"])
            if "logo" in matchup["away_team"]:
                matchup["away_team"]["logo"] = cache_logo(matchup["away_team"]["logo"])

        for score in weekly_scores:
            if "logo" in score:
                score["logo"] = cache_logo(score["logo"])

        standings = self.data.get_standings()
        for team in standings:
            team.logo = cache_logo(team.logo_url)

        power_rankings = self.data.get_power_rankings(week)
        for rank in power_rankings:
            rank[1].logo = cache_logo(rank[1].logo_url)

        top_week = self.data.get_top_scored_week()
        if top_week and top_week[0]:
            top_week[0].logo = cache_logo(top_week[0].logo_url)

        low_week = self.data.get_least_scored_week()
        if low_week and low_week[0]:
            low_week[0].logo = cache_logo(low_week[0].logo_url)

        top_scorer = self.data.get_top_scorer()
        if top_scorer:
            top_scorer.logo = cache_logo(top_scorer.logo_url)

        low_scorer = self.data.get_least_scorer()
        if low_scorer:
            low_scorer.logo = cache_logo(low_scorer.logo_url)

        most_pa = self.data.get_most_points_against()
        if most_pa:
            most_pa.logo = cache_logo(most_pa.logo_url)

        # Initialize features
        feature_cache_dir = Path("cache/features")
        beef_feature = BeefFeature(data_dir=feature_cache_dir)
        high_roller_feature = HighRollerFeature(
            season=self.year, data_dir=feature_cache_dir
        )
        attendance_feature = AttendanceFeature(data_dir=feature_cache_dir, week=week)
        geocoder = Geocoder()  # Instantiate Geocoder

        # Process attendance_feature.feature_data to make it easily searchable
        # This will store game details (date, attendance, city, state, country, latlng) per pro_team
        pro_team_game_data = {}
        for game in attendance_feature.feature_data:
            game_location_address = (
                f"{game['city']}, {game['state']}, {game['country']}"
            )
            print(f"Geocoding address: {game_location_address}")
            location = geocoder.geocode(game_location_address)
            game_latlng = None
            if location:
                game_latlng = (location.latitude, location.longitude)

            game_details = {
                "date": game["date"],
                "attendance": game["attendance"],
                "city": game["city"],
                "state": game["state"],
                "country": game["country"],
                "latlng": game_latlng,
            }

            # Store game details for both home and away teams
            if game["home_team_abbrev"] not in pro_team_game_data:
                pro_team_game_data[game["home_team_abbrev"]] = []
            pro_team_game_data[game["home_team_abbrev"]].append(game_details)

            if game["away_team_abbrev"] not in pro_team_game_data:
                pro_team_game_data[game["away_team_abbrev"]] = []
            pro_team_game_data[game["away_team_abbrev"]].append(game_details)

        all_players = self.data.get_weekly_players(week)
        for player in all_players:
            player["team_logo"] = cache_logo(player["team_logo"])
            if player["pro_team"] and player["pro_team"] != "None":
                player["pro_team_logo"] = cache_logo(
                    f"images/logo_svg/{player['pro_team']}.svg"
                )
            else:
                player["pro_team_logo"] = None
            # Add game data for the player's pro team
            player["game_data"] = pro_team_game_data.get(player["pro_team"], [])

            # Add feature stats
            name_parts = player["name"].split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            player["beef_weight"] = beef_feature.get_player_weight(
                first_name, last_name, player["pro_team"], player["position"]
            )

            player["beef_height"] = beef_feature.get_player_height(
                first_name, last_name, player["pro_team"], player["position"]
            )
            player["beef_tabbu"] = beef_feature.get_player_tabbu(
                first_name, last_name, player["pro_team"], player["position"]
            )

            player["beef_height_inches"] = beef_feature.get_player_height_inches(
                first_name, last_name, player["pro_team"], player["position"]
            )

            player["beef_years_exp"] = beef_feature.get_player_years_exp(
                first_name, last_name, player["pro_team"], player["position"]
            )

            player["beef_age"] = beef_feature.get_player_age(
                first_name, last_name, player["pro_team"], player["position"]
            )

            player["beef_birth_date"] = beef_feature.get_player_birth_date(
                first_name, last_name, player["pro_team"], player["position"]
            )

            # Calculate zodiac sign
            player["zodiac_emoji"] = self.get_zodiac_emoji(player["beef_birth_date"])

            player["high_roller_fines"] = high_roller_feature.get_player_fines_total(
                first_name, last_name, player["pro_team"], player["position"]
            )
        top_overall, top_by_position = calculate_top_players(all_players)

        # --- Upcoming & Recent Birthdays ---
        upcoming_recent_birthdays = []
        seven_days_ago = target_monday_date - timedelta(days=7)
        seven_days_from_now = target_monday_date + timedelta(days=7)

        for player in all_players:
            # Only consider players on fantasy teams (not free agents)
            if player["team_abbrev"] != "FA" and player["beef_birth_date"]:
                try:
                    # Parse birth date string (assuming YYYY-MM-DD format)
                    birth_date_obj = datetime.strptime(
                        player["beef_birth_date"], "%Y-%m-%d"
                    ).date()

                    # Create a birthday for the current year of the report week
                    current_year_birthday = birth_date_obj.replace(
                        year=target_monday_date.year
                    )

                    # Adjust for birthdays that might have just passed in the previous year
                    # or are coming up in the next year, relative to the current week's year
                    if current_year_birthday < seven_days_ago:
                        current_year_birthday = current_year_birthday.replace(
                            year=target_monday_date.year + 1
                        )
                    elif current_year_birthday > seven_days_from_now:
                        current_year_birthday = current_year_birthday.replace(
                            year=target_monday_date.year - 1
                        )

                    # Check if the birthday falls within the 14-day window
                    if seven_days_ago <= current_year_birthday <= seven_days_from_now:
                        upcoming_recent_birthdays.append(
                            {
                                "name": player["name"],
                                "team_name": player["team_name"],
                                "team_logo": player["team_logo"],  # Fantasy team logo
                                "pro_team_logo": player[
                                    "pro_team_logo"
                                ],  # Pro team logo
                                "position": player["position"],
                                "birth_date": current_year_birthday.strftime(
                                    "%b %d"
                                ),  # Format as 'Mon DD'
                            }
                        )
                except ValueError:
                    # Handle cases where birth_date might not be in expected format
                    pass

        # Sort birthdays by date (descending)
        upcoming_recent_birthdays.sort(
            key=lambda x: datetime.strptime(x["birth_date"], "%b %d").replace(
                year=target_monday_date.year
            ),
            reverse=True,
        )

        # --- New Points Per Player Per Position ---

        # Helper for sorting players
        pos_order = ["QB", "RB", "WR", "TE", "FLEX", "D/ST", "K", "P"]

        def get_player_sort_key(player):
            slot = player["slot_position"]
            if slot == "BE" or slot == "IR":
                return (1, 0)  # Bench players last
            try:
                return (0, pos_order.index(slot))
            except ValueError:
                return (0, len(pos_order))  # Other starters after defined order

        # Group players by team
        players_by_team = {}
        # Create a mapping from team_name to the actual Team object for easy lookup
        team_name_to_object = {team.team_name: team for team in self.data.league.teams}

        for player in all_players:
            team_name = player["team_name"]
            if team_name not in players_by_team:
                players_by_team[team_name] = {
                    "team_object": (
                        team_name_to_object.get(team_name)
                        if team_name != "Free Agent"
                        else None
                    ),
                    "players": [],
                    "grouped_points_breakdown": {},
                    "detailed_points_breakdown": [],
                }
            players_by_team[team_name]["players"].append(player)

        # Exclude "Free Agent" team from further processing for display in "Points Per Player Breakdown"
        if "Free Agent" in players_by_team:
            del players_by_team["Free Agent"]

        # Process stats for each player and sort
        stat_name_to_id_map = {v: int(k) for k, v in PLAYER_STATS_MAP.items()}
        for team_name, team_data in players_by_team.items():
            for player in team_data["players"]:
                # Normalize stats table
                actual_breakdown = player.get("points_breakdown") or {}
                proj_breakdown = player.get("projected_points_breakdown") or {}

                all_stat_names = set(actual_breakdown.keys()) | set(
                    proj_breakdown.keys()
                )

                stat_ids = [
                    stat_name_to_id_map.get(name)
                    for name in all_stat_names
                    if stat_name_to_id_map.get(name) is not None
                ]

                # Create a list of stat info objects to sort by abbr
                stats_to_display = []
                for stat_id in stat_ids:
                    stat_name = PLAYER_STATS_MAP.get(stat_id)
                    header_info = SETTINGS_SCORING_FORMAT_MAP.get(stat_id, {})
                    stats_to_display.append(
                        {
                            "id": stat_id,
                            "name": stat_name,
                            "abbr": header_info.get("abbr", stat_name or str(stat_id)),
                            "label": header_info.get(
                                "label", stat_name or str(stat_id)
                            ),
                        }
                    )

                stats_to_display.sort(key=lambda x: x["abbr"])

                headers = []
                actual_row = []
                proj_row = []

                for stat_info in stats_to_display:
                    stat_name = stat_info["name"]

                    headers.append(
                        {"abbr": stat_info["abbr"], "label": stat_info["label"]}
                    )

                    actual_pts = actual_breakdown.get(stat_name, 0.0)
                    proj_pts = proj_breakdown.get(stat_name, 0.0)

                    actual_style = ""
                    proj_style = ""
                    if actual_pts == proj_pts:
                        actual_style = "light-blue"
                        proj_style = "light-blue"
                    elif actual_pts > proj_pts:
                        actual_style = "light-green"
                    else:
                        proj_style = "light-red"

                    actual_row.append({"value": actual_pts, "style": actual_style})
                    proj_row.append({"value": proj_pts, "style": proj_style})

                player["stats_table"] = {
                    "headers": headers,
                    "actual": actual_row,
                    "projected": proj_row,
                }

            team_data["players"].sort(key=get_player_sort_key)

        # Calculate team-specific points breakdowns
        for team_name, team_data in players_by_team.items():
            team_all_players = team_data["players"]
            team_aggregated_points_by_id = {}

            for player in team_all_players:
                if (
                    player["slot_position"] == "BE"  or player["slot_position"] == "IR"
                ):  # Only consider starters for team breakdown
                    continue
                if "points_breakdown" in player and player["points_breakdown"]:
                    for stat_name, points in player["points_breakdown"].items():
                        if isinstance(stat_name, str) and isinstance(
                            points, (int, float)
                        ):
                            stat_id = stat_name_to_id_map.get(stat_name)
                            if stat_id:
                                team_aggregated_points_by_id[stat_id] = (
                                    team_aggregated_points_by_id.get(stat_id, 0.0)
                                    + points
                                )

            team_detailed_points_breakdown = []
            for stat_id, total_points in team_aggregated_points_by_id.items():
                stat_name = PLAYER_STATS_MAP.get(int(stat_id))
                category = (
                    STAT_CATEGORY_LOOKUP.get(stat_name, "Other")
                    if stat_name
                    else "Other"
                )
                try:
                    label = SETTINGS_SCORING_FORMAT_MAP.get(int(stat_id), {}).get(
                        "label", stat_name or stat_id
                    )
                except (ValueError, TypeError):
                    label = stat_name or stat_id

                team_detailed_points_breakdown.append(
                    {"label": label, "category": category, "total_points": total_points}
                )

            team_detailed_points_breakdown.sort(
                key=lambda x: (x["category"], x["label"])
            )

            team_grouped_points_breakdown = {}
            for item in team_detailed_points_breakdown:
                category = item["category"]
                team_grouped_points_breakdown[category] = (
                    team_grouped_points_breakdown.get(category, 0.0)
                    + item["total_points"]
                )

            team_data["grouped_points_breakdown"] = dict(
                sorted(team_grouped_points_breakdown.items())
            )
            team_data["detailed_points_breakdown"] = team_detailed_points_breakdown

            # Calculate team-level beef statistics (averages)
            team_players = team_data["players"]
            valid_weights = [
                p["beef_weight"]
                for p in team_players
                if p["beef_weight"] > 0 and p["slot_position"] != "D/ST"
            ]
            valid_heights = [
                p["beef_height_inches"]
                for p in team_players
                if p["beef_height_inches"] > 0
            ]
            valid_ages = [p["beef_age"] for p in team_players if p["beef_age"] > 0]
            valid_years_exp = [
                p["beef_years_exp"] for p in team_players if p["beef_years_exp"] > 0
            ]

            team_data["avg_weight"] = (
                sum(valid_weights) / len(valid_weights) if valid_weights else 0
            )
            team_data["avg_height_inches"] = (
                sum(valid_heights) / len(valid_heights) if valid_heights else 0
            )
            team_data["avg_age"] = (
                sum(valid_ages) / len(valid_ages) if valid_ages else 0
            )
            team_data["avg_years_exp"] = (
                sum(valid_years_exp) / len(valid_years_exp) if valid_years_exp else 0
            )

            # Convert average height back to feet'inches format
            if team_data["avg_height_inches"] > 0:
                total_inches = int(round(team_data["avg_height_inches"]))
                feet = total_inches // 12
                inches = total_inches % 12
                team_data["avg_height"] = f"{feet}'{inches}\""
            else:
                team_data["avg_height"] = "0'0\""

            # Calculate zodiac distribution for this team
            team_zodiac_counts = {}
            zodiac_players = [
                p
                for p in team_players
                if p.get("position") != "D/ST" and p.get("zodiac_emoji")
            ]

            for player in zodiac_players:
                zodiac = player["zodiac_emoji"]
                if zodiac:
                    team_zodiac_counts[zodiac] = team_zodiac_counts.get(zodiac, 0) + 1

            # Create sorted zodiac chart data for this team
            sorted_zodiac_signs = (
                sorted(team_zodiac_counts.keys()) if team_zodiac_counts else []
            )
            zodiac_chart_labels = [
                f"{emoji} {self.get_zodiac_name(emoji)}"
                for emoji in sorted_zodiac_signs
            ]
            zodiac_chart_data = [
                team_zodiac_counts.get(zodiac, 0) for zodiac in sorted_zodiac_signs
            ]

            team_data["zodiac_chart_data"] = {
                "labels": zodiac_chart_labels,
                "data": zodiac_chart_data,
            }

        # Prepare data for radar charts
        all_stat_categories = set()
        for team_name, team_data in players_by_team.items():
            all_stat_categories.update(team_data["grouped_points_breakdown"].keys())

        sorted_stat_categories = sorted(list(all_stat_categories))

        for team_name, team_data in players_by_team.items():
            team_points_data = []
            for category in sorted_stat_categories:
                team_points_data.append(
                    team_data["grouped_points_breakdown"].get(category, 0.0)
                )

            team_data["radar_chart_data"] = {
                "labels": sorted_stat_categories,
                "datasets": [{"label": team_name, "data": team_points_data}],
            }

        # Calculate team demographics for weekly report
        teams_with_data = []
        for team_name, team_data in players_by_team.items():
            if team_data["avg_age"] > 0:  # Only include teams with valid data
                teams_with_data.append(
                    {
                        "name": team_name,
                        "team_object": team_data["team_object"],
                        "avg_age": team_data["avg_age"],
                        "avg_years_exp": team_data["avg_years_exp"],
                        "avg_height_inches": team_data["avg_height_inches"],
                        "avg_height": team_data["avg_height"],
                    }
                )

        # Calculate demographics extremes
        oldest_team = (
            max(teams_with_data, key=lambda x: x["avg_age"])
            if teams_with_data
            else None
        )
        youngest_team = (
            min(teams_with_data, key=lambda x: x["avg_age"])
            if teams_with_data
            else None
        )
        most_experienced_team = (
            max(teams_with_data, key=lambda x: x["avg_years_exp"])
            if teams_with_data
            else None
        )
        least_experienced_team = (
            min(teams_with_data, key=lambda x: x["avg_years_exp"])
            if teams_with_data
            else None
        )
        tallest_team = (
            max(teams_with_data, key=lambda x: x["avg_height_inches"])
            if teams_with_data
            else None
        )
        shortest_team = (
            min(teams_with_data, key=lambda x: x["avg_height_inches"])
            if teams_with_data
            else None
        )

        # Calculate individual player demographics
        all_players_with_beef = []
        for team_name, team_data in players_by_team.items():
            for player in team_data["players"]:
                if player["beef_age"] > 0:  # Only include players with valid data
                    all_players_with_beef.append(
                        {
                            "name": player["name"],
                            "position": player["position"],
                            "pro_team": player["pro_team"],
                            "team_name": team_name,
                            "team_logo": player["team_logo"],
                            "beef_age": player["beef_age"],
                            "beef_years_exp": player["beef_years_exp"],
                            "beef_height_inches": player["beef_height_inches"],
                            "beef_height": player["beef_height"],
                        }
                    )

        # Calculate individual player extremes
        oldest_player = (
            max(all_players_with_beef, key=lambda x: x["beef_age"])
            if all_players_with_beef
            else None
        )
        youngest_player = (
            min(all_players_with_beef, key=lambda x: x["beef_age"])
            if all_players_with_beef
            else None
        )
        most_experienced_player = (
            max(all_players_with_beef, key=lambda x: x["beef_years_exp"])
            if all_players_with_beef
            else None
        )
        least_experienced_player = (
            min(all_players_with_beef, key=lambda x: x["beef_years_exp"])
            if all_players_with_beef
            else None
        )
        tallest_player = (
            max(all_players_with_beef, key=lambda x: x["beef_height_inches"])
            if all_players_with_beef
            else None
        )
        shortest_player = (
            min(all_players_with_beef, key=lambda x: x["beef_height_inches"])
            if all_players_with_beef
            else None
        )

        # --- Points Breakdown Refactored ---

        # Aggregate points by stat ID
        stat_name_to_id_map = {v: k for k, v in PLAYER_STATS_MAP.items()}
        aggregated_points_by_id = {}
        for player in all_players:
            if player["team_abbrev"] == "FA" or player["slot_position"] == "BE" or player["slot_position"] == "IR":
                continue
            if "points_breakdown" in player and player["points_breakdown"]:
                for stat_name, points in player["points_breakdown"].items():
                    if isinstance(stat_name, str) and isinstance(points, (int, float)):
                        stat_id = stat_name_to_id_map.get(stat_name)
                        if stat_id:
                            aggregated_points_by_id[stat_id] = (
                                aggregated_points_by_id.get(stat_id, 0.0) + points
                            )

        # Create detailed breakdown with all necessary info
        detailed_points_breakdown = []
        for stat_id, total_points in aggregated_points_by_id.items():
            # PLAYER_STATS_MAP is {id: name}, but id is a string. Let's be safe.
            stat_name = PLAYER_STATS_MAP.get(int(stat_id))
            category = (
                STAT_CATEGORY_LOOKUP.get(stat_name, "Other") if stat_name else "Other"
            )

            # SETTINGS_SCORING_FORMAT_MAP is {id: object}, id is an int.
            # Let's ensure we handle string/int keys properly.
            try:
                label = SETTINGS_SCORING_FORMAT_MAP.get(int(stat_id), {}).get(
                    "label", stat_name or stat_id
                )
            except (ValueError, TypeError):
                label = stat_name or stat_id

            detailed_points_breakdown.append(
                {"label": label, "category": category, "total_points": total_points}
            )

        # Sort by category, then by label
        detailed_points_breakdown.sort(key=lambda x: (x["category"], x["label"]))

        # Create grouped breakdown for the pie chart
        grouped_points_breakdown = {}
        for item in detailed_points_breakdown:
            category = item["category"]
            grouped_points_breakdown[category] = (
                grouped_points_breakdown.get(category, 0.0) + item["total_points"]
            )

        # Sort the grouped data by category for consistent display
        sorted_grouped_points_breakdown = dict(sorted(grouped_points_breakdown.items()))

        # Prepare data for radar charts
        all_stat_categories = set()
        for team_name, team_data in players_by_team.items():
            all_stat_categories.update(team_data["grouped_points_breakdown"].keys())

        sorted_stat_categories = sorted(list(all_stat_categories))

        radar_datasets = []
        for team_name, team_data in players_by_team.items():
            team_points_data = []
            for category in sorted_stat_categories:
                team_points_data.append(
                    team_data["grouped_points_breakdown"].get(category, 0.0)
                )

            radar_datasets.append({"label": team_name, "data": team_points_data})

        final_radar_chart_data = {
            "labels": sorted_stat_categories,
            "datasets": radar_datasets,
        }

        # Helper map for weekly scores to get logo and division easily
        team_info_map = {score['name']: score for score in weekly_scores}

        # --- Beef Rankings ---
        beef_rankings = []
        for team_name, team_data in players_by_team.items():
            team_players = team_data["players"]
            # Filter for players that contribute to beef rankings (not D/ST)
            beefy_players = [
                p
                for p in team_players
                if p.get("position") != "D/ST" and p.get("beef_tabbu") is not None
            ]

            total_weight = sum(p.get("beef_weight", 0) for p in beefy_players)
            # Calculate TABBU from total weight to avoid rounding errors
            total_tabbu = total_weight / 500.0

            if total_tabbu > 0:
                # Get win status from team_info_map
                won = False
                if team_name in team_info_map:
                    won = team_info_map[team_name]['won']

                beef_rankings.append(
                    {
                        "team_name": team_name,
                        "team_logo": team_data["players"][0]["team_logo"],
                        "total_weight": total_weight,
                        "total_tabbu": total_tabbu,
                        "won": won,
                    }
                )

        # Sort by total_tabbu descending
        beef_rankings.sort(key=lambda x: x["total_tabbu"], reverse=True)

        # Add rank and emoji representation
        for i, team in enumerate(beef_rankings):
            team["rank"] = i + 1
            total_tabbu = team["total_tabbu"]

            # 1 cow = 1200 lb . 1 tabbu = 500 lb . 1 beef = 0.5 tabbu. Round to nearest 0.5.
            total_tabbu_rounded = round(total_tabbu * 2) / 2
            num_cows = int(total_tabbu_rounded // 2.4)
            remaining_tabbu = total_tabbu_rounded - (num_cows * 2.4)
            num_beefs = int(remaining_tabbu / 0.5)

            team["tabbu_emojis"] = "🐮" * num_cows + "🥩" * num_beefs

        # --- Zodiac Rankings ---
        # Calculate zodiac distribution for each team
        zodiac_team_data = []
        all_zodiac_signs = set()
        league_zodiac_counts = {}

        for team_name, team_data in players_by_team.items():
            team_players = team_data["players"]
            # Filter for players with valid zodiac data (not D/ST)
            zodiac_players = [
                p
                for p in team_players
                if p.get("position") != "D/ST" and p.get("zodiac_emoji")
            ]

            team_zodiac_counts = {}
            for player in zodiac_players:
                zodiac = player["zodiac_emoji"]
                if zodiac:
                    team_zodiac_counts[zodiac] = team_zodiac_counts.get(zodiac, 0) + 1
                    league_zodiac_counts[zodiac] = (
                        league_zodiac_counts.get(zodiac, 0) + 1
                    )
                    all_zodiac_signs.add(zodiac)

            if team_zodiac_counts:
                zodiac_team_data.append(
                    {
                        "team_name": team_name,
                        "team_logo": team_data["players"][0]["team_logo"],
                        "zodiac_counts": team_zodiac_counts,
                        "total_players": sum(team_zodiac_counts.values()),
                    }
                )

        # Sort zodiac signs for consistent ordering and create labels with names
        sorted_zodiac_signs = sorted(list(all_zodiac_signs))
        zodiac_chart_labels = [
            f"{emoji} {self.get_zodiac_name(emoji)}" for emoji in sorted_zodiac_signs
        ]

        # Prepare radar chart data for zodiac
        zodiac_radar_datasets = []
        for team_data in zodiac_team_data:
            team_zodiac_data = []
            for zodiac in sorted_zodiac_signs:
                team_zodiac_data.append(team_data["zodiac_counts"].get(zodiac, 0))

            zodiac_radar_datasets.append(
                {"label": team_data["team_name"], "data": team_zodiac_data}
            )

        zodiac_radar_chart_data = {
            "labels": zodiac_chart_labels,
            "datasets": zodiac_radar_datasets,
        }

        # Prepare pie chart data for league-wide zodiac distribution
        zodiac_pie_chart_data = {
            "labels": zodiac_chart_labels,
            "data": [
                league_zodiac_counts.get(zodiac, 0) for zodiac in sorted_zodiac_signs
            ],
        }

        # --- Touchdowns Calculation ---
        scoring_format = self.data.league.settings.scoring_format
        stat_name_to_id = {v: k for k, v in PLAYER_STATS_MAP.items()}
        stat_points_map = {}
        for item in scoring_format:
            stat_id = item['id']
            points = item['points']
            if stat_id in PLAYER_STATS_MAP:
                stat_name = PLAYER_STATS_MAP[stat_id]
                stat_points_map[stat_name] = points

        td_categories = {
            "pass": ["passingTouchdowns"],
            "rush": ["rushingTouchdowns"],
            "recv": ["receivingTouchdowns"],
            "def": [
                "kickoffReturnTouchdowns",
                "puntReturnTouchdowns",
                "interceptionReturnTouchdowns",
                "fumbleReturnTouchdowns",
                "fumbleRecoveredForTD",
                "defensiveBlockedKickForTouchdowns"
            ]
        }

        # Helper map for weekly scores to get logo and division easily
        team_info_map = {score['name']: score for score in weekly_scores}

        touchdown_standings = []

        for team_name, team_data in players_by_team.items():
            td_stats = {
                "name": team_name,
                "pass": 0, "rush": 0, "recv": 0, "def": 0, "total": 0,
                "def_breakdown": {
                    "defensiveBlockedKickForTouchdowns": 0,
                    "fumbleReturnTouchdowns": 0,
                    "fumbleRecoveredForTD": 0,
                    "interceptionReturnTouchdowns": 0,
                    "puntReturnTouchdowns": 0,
                    "kickoffReturnTouchdowns": 0
                }
            }
            
            # Get logo and division from weekly_scores map
            if team_name in team_info_map:
                info = team_info_map[team_name]
                td_stats['logo'] = info['logo']
                td_stats['division'] = info['division']
                td_stats['won'] = info['won'] # Reuse for '?' column
            else:
                 # Fallback
                td_stats['logo'] = team_data["players"][0]["team_logo"]
                td_stats['division'] = "Unknown"
                td_stats['won'] = False

            for player in team_data["players"]:
                # Only Starters
                if player['slot_position'] in ['BE', 'IR']:
                    continue

                breakdown = player.get('points_breakdown', {})
                for cat_type, stat_names in td_categories.items():
                    for stat_name in stat_names:
                        if stat_name in breakdown:
                            points = breakdown[stat_name]
                            pts_per_unit = stat_points_map.get(stat_name)
                            if pts_per_unit:
                                count = int(round(points / pts_per_unit))
                                td_stats[cat_type] += count
                                td_stats["total"] += count
                                
                                if cat_type == "def" and stat_name in td_stats["def_breakdown"]:
                                    td_stats["def_breakdown"][stat_name] += count
            
            touchdown_standings.append(td_stats)

        # Sort: Total DESC > Def DESC > Rush DESC > Recv DESC > Pass DESC
        # Tie breaker for Def: BLKKRTD > FRTD/FTD > INTTD > PRTD > KRTD
        def td_sort_key(item):
            primary = (
                item['total'],
                item['def'],
                item['rush'],
                item['recv'],
                item['pass']
            )
            def_sub = (
                item['def_breakdown']['defensiveBlockedKickForTouchdowns'],
                item['def_breakdown']['fumbleReturnTouchdowns'] + item['def_breakdown']['fumbleRecoveredForTD'],
                item['def_breakdown']['interceptionReturnTouchdowns'],
                item['def_breakdown']['puntReturnTouchdowns'],
                item['def_breakdown']['kickoffReturnTouchdowns']
            )
            return primary + def_sub

        touchdown_standings.sort(key=td_sort_key, reverse=True)

        # Calculate faked location, time, and attendance for each matchup
        for matchup in matchups:
            home_team_name = matchup["home_team"]["name"]
            away_team_name = matchup["away_team"]["name"]

            home_starters_game_data = []
            away_starters_game_data = []

            # Collect game data for home team starters
            if home_team_name in players_by_team:
                for player in players_by_team[home_team_name]["players"]:
                    if player["slot_position"] != "BE":  # Only starters
                        home_starters_game_data.extend(player.get("game_data", []))

            # Collect game data for away team starters
            if away_team_name in players_by_team:
                for player in players_by_team[away_team_name]["players"]:
                    if player["slot_position"] != "BE":  # Only starters
                        away_starters_game_data.extend(player.get("game_data", []))

            home_faked_data = self._calculate_faked_data(home_starters_game_data)
            away_faked_data = self._calculate_faked_data(away_starters_game_data)

            # Average home and away faked data for the matchup
            combined_faked_data = {}
            if (
                home_faked_data["avg_lat"] is not None
                and away_faked_data["avg_lat"] is not None
            ):
                combined_faked_data["avg_lat"] = (
                    home_faked_data["avg_lat"] + away_faked_data["avg_lat"]
                ) / 2
                combined_faked_data["avg_lon"] = (
                    home_faked_data["avg_lon"] + away_faked_data["avg_lon"]
                ) / 2
            else:
                combined_faked_data["avg_lat"] = (
                    home_faked_data["avg_lat"] or away_faked_data["avg_lat"]
                )
                combined_faked_data["avg_lon"] = (
                    home_faked_data["avg_lon"] or away_faked_data["avg_lon"]
                )

            if (
                home_faked_data["avg_attendance"] is not None
                and away_faked_data["avg_attendance"] is not None
            ):
                combined_faked_data["avg_attendance"] = (
                    home_faked_data["avg_attendance"]
                    + away_faked_data["avg_attendance"]
                ) / 2
            else:
                combined_faked_data["avg_attendance"] = (
                    home_faked_data["avg_attendance"]
                    or away_faked_data["avg_attendance"]
                )

            if (
                home_faked_data["avg_timestamp"] is not None
                and away_faked_data["avg_timestamp"] is not None
            ):
                combined_faked_data["avg_timestamp"] = (
                    home_faked_data["avg_timestamp"] + away_faked_data["avg_timestamp"]
                ) / 2
            else:
                combined_faked_data["avg_timestamp"] = (
                    home_faked_data["avg_timestamp"] or away_faked_data["avg_timestamp"]
                )

            # Perform final reverse geocoding and formatting
            faked_location_address = "N/A"
            if (
                combined_faked_data["avg_lat"] is not None
                and combined_faked_data["avg_lon"] is not None
            ):
                # First, try to find a nearby stadium
                print(
                    f"Searching for nearby stadiums for {combined_faked_data['avg_lat']}, {combined_faked_data['avg_lon']}"
                )
                nearby_stadiums = geocoder.find_nearby_stadiums(
                    combined_faked_data["avg_lat"], combined_faked_data["avg_lon"]
                )

                chosen_stadium = None
                for stadium in nearby_stadiums:
                    if stadium["name"] != "Unnamed Stadium":
                        chosen_stadium = stadium
                        break
                print("CHOSEN STADIUM")
                print(json.dumps(chosen_stadium))

                if chosen_stadium:
                    try:
                        # Reverse geocode the stadium's coordinates to get city/state
                        stadium_reverse_location = geocoder.reverse_geocode(
                            chosen_stadium["lat"],
                            chosen_stadium["lon"],
                        )
                        if stadium_reverse_location:
                            state = stadium_reverse_location.raw["address"]["state"]
                            faked_location_address = (
                                f"{chosen_stadium['name']}, {state}"
                            )
                        else:
                            faked_location_address = f"{chosen_stadium['name']}"
                    except Exception as e:
                        print(f"Error during reverse geocoding for chosen stadium: {e}")
                        faked_location_address = f"{chosen_stadium['name']}"
                        # faked_location_address = f"{chosen_stadium['name']} (Lat: {chosen_stadium['lat']:.4f}, Lon: {chosen_stadium['lon']:.4f})"
                else:
                    # Fallback to reverse geocoding if no named stadium is found
                    try:
                        reverse_location = geocoder.reverse_geocode(
                            combined_faked_data["avg_lat"],
                            combined_faked_data["avg_lon"],
                        )
                        if reverse_location:
                            faked_location_address = f"{reverse_location.raw['name']}, {reverse_location.raw['address']['state']}"
                    except Exception as e:
                        print(f"Error during reverse geocoding for matchup: {e}")

            faked_date = "N/A"
            if combined_faked_data["avg_timestamp"] is not None:
                faked_date = datetime.fromtimestamp(
                    combined_faked_data["avg_timestamp"]
                ).strftime("%Y-%m-%d")

            faked_attendance = "N/A"
            if combined_faked_data["avg_attendance"] is not None:
                faked_attendance = round(combined_faked_data["avg_attendance"])

            matchup["faked_matchup_data"] = {
                "location": faked_location_address,
                "date": faked_date,
                "attendance": faked_attendance,
            }
        # Prepare template context
        context = {
            "year": self.year,
            "week": week,
            "matchups": matchups,
            "weekly_scores": weekly_scores,
            "players_by_team": players_by_team,  # New data structure
            "standings": standings,
            "power_rankings": power_rankings,
            "top_week": top_week,
            "low_week": low_week,
            "top_scorer": top_scorer,
            "low_scorer": low_scorer,
            "most_pa": most_pa,
            "top_overall_players": top_overall,
            "top_players_by_position": top_by_position,
            "largest_weekly_margin": largest_weekly_margin,
            "largest_season_margin": largest_season_margin,
            "upcoming_recent_birthdays": upcoming_recent_birthdays,
            "oldest_team": oldest_team,
            "youngest_team": youngest_team,
            "most_experienced_team": most_experienced_team,
            "least_experienced_team": least_experienced_team,
            "tallest_team": tallest_team,
            "shortest_team": shortest_team,
            "oldest_player": oldest_player,
            "youngest_player": youngest_player,
            "most_experienced_player": most_experienced_player,
            "least_experienced_player": least_experienced_player,
            "tallest_player": tallest_player,
            "shortest_player": shortest_player,
            "grouped_points_breakdown": sorted_grouped_points_breakdown,
            "detailed_points_breakdown": detailed_points_breakdown,
            "radar_chart_data": final_radar_chart_data,  # Use the new structure
            "beef_rankings": beef_rankings,
            "zodiac_radar_chart_data": zodiac_radar_chart_data,
            "zodiac_pie_chart_data": zodiac_pie_chart_data,
            "touchdown_standings": touchdown_standings,
            "zodiac_names": {
                "♈": "Aries",
                "♉": "Taurus",
                "♊": "Gemini",
                "♋": "Cancer",
                "♌": "Leo",
                "♍": "Virgo",
                "♎": "Libra",
                "♏": "Scorpio",
                "♐": "Sagittarius",
                "♑": "Capricorn",
                "♒": "Aquarius",
                "♓": "Pisces",
            },
        }

        # Render the template
        html = self.template.render_weekly_report(context)

        # Determine output file path
        if output_file is None:
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{self.year}-week{week}.html")

        # Write the HTML to the file
        with open(output_file, "w") as f:
            f.write(html)

        return output_file
