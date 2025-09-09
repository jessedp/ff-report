"""Generate fantasy football reports"""

import os
import hashlib
import urllib.request
import shutil
from .data import LeagueData
from .stats import (
    calculate_weekly_scores,
    calculate_matchups,
    points_per_player_per_position,
    calculate_top_players,
)
from .templates import TemplateEngine
from .config import LEAGUE_YEAR, SWID, ESPN_S2


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
            with urllib.request.urlopen(req) as response, open(
                local_path, "wb"
            ) as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(
                f"Error downloading logo: {logo_url_to_download} - {e}"
            )  # Print the URL that failed
            # Fallback to default image
            default_logo_filename = "placeholder.png"
            default_logo_source_path = os.path.join(
                "images", default_logo_filename
            )

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
                print(
                    f"Error copying default logo to cache: {copy_e}. Returning None."
                )
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
        matchups = calculate_matchups(box_scores)
        weekly_scores = calculate_weekly_scores(box_scores)

        # Sort weekly scores by score (highest first)
        weekly_scores.sort(key=lambda x: x["score"], reverse=True)

        # --- Logo Caching ---
        for matchup in matchups:
            matchup["home_team"]["logo"] = cache_logo(
                matchup["home_team"]["logo"]
            )
            matchup["away_team"]["logo"] = cache_logo(
                matchup["away_team"]["logo"]
            )

        # Calculate position stats for all teams
        position_stats = {}
        for team in weekly_scores:
            position_stats[team["name"]] = points_per_player_per_position(
                team["lineup"]
            )

        # Get top player stats
        all_players = self.data.get_weekly_players(week)
        for player in all_players:
            player["team_logo"] = cache_logo(player["team_logo"])
        top_overall, top_by_position = calculate_top_players(all_players)

        # Prepare template context
        context = {
            "year": self.year,
            "week": week,
            "matchups": matchups,
            "weekly_scores": weekly_scores,
            "position_stats": position_stats,
            "standings": self.data.get_standings(),
            "power_rankings": self.data.get_power_rankings(week),
            "top_week": self.data.get_top_scored_week(),
            "low_week": self.data.get_least_scored_week(),
            "top_scorer": self.data.get_top_scorer(),
            "low_scorer": self.data.get_least_scorer(),
            "most_pa": self.data.get_most_points_against(),
            "top_overall_players": top_overall,
            "top_players_by_position": top_by_position,
        }

        # Render the template
        html = self.template.render_weekly_report(context)

        # Determine output file path
        if output_file is None:
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(
                output_dir, f"{self.year}-week{week}.html"
            )

        # Write the HTML to the file
        with open(output_file, "w") as f:
            f.write(html)

        return output_file
