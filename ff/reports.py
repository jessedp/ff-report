"""Generate fantasy football reports"""

import os
import hashlib
import urllib.request
import shutil
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

        # --- Margin of Victory ---
        team_abbrev_to_name = {team.team_abbrev: team.team_name for team in self.data.league.teams}

        largest_weekly_margin = None
        max_weekly_margin = -1

        for matchup in matchups:
            margin = abs(matchup['home_team']['score'] - matchup['away_team']['score'])
            if margin > max_weekly_margin:
                max_weekly_margin = margin
                if matchup['winner'] == 'home':
                    winner = matchup['home_team']
                    loser = matchup['away_team']
                else:
                    winner = matchup['away_team']
                    loser = matchup['home_team']
                
                winner_name = team_abbrev_to_name.get(winner['abbrev'])
                
                largest_weekly_margin = {
                    'winner_name': winner_name,
                    'winner_score': winner['score'],
                    'loser_score': loser['score'],
                    'margin': margin
                }

        largest_season_margin = None
        max_season_margin = -1

        for w in range(1, week + 1):
            weekly_box_scores = self.data.get_box_scores(w)
            weekly_matchups = calculate_matchups(weekly_box_scores)
            for matchup in weekly_matchups:
                margin = abs(matchup['home_team']['score'] - matchup['away_team']['score'])
                if margin > max_season_margin:
                    max_season_margin = margin
                    if matchup['winner'] == 'home':
                        winner = matchup['home_team']
                        loser = matchup['away_team']
                    else:
                        winner = matchup['away_team']
                        loser = matchup['home_team']
                    
                    winner_name = team_abbrev_to_name.get(winner['abbrev'])
                    
                    largest_season_margin = {
                        'winner_name': winner_name,
                        'winner_score': winner['score'],
                        'loser_score': loser['score'],
                        'margin': margin
                    }

        # --- Logo Caching ---
        for matchup in matchups:
            matchup["home_team"]["logo"] = cache_logo(
                matchup["home_team"]["logo"]
            )
            matchup["away_team"]["logo"] = cache_logo(
                matchup["away_team"]["logo"]
            )

        # Get top player stats
        all_players = self.data.get_weekly_players(week)
        for player in all_players:
            player["team_logo"] = cache_logo(player["team_logo"])
        top_overall, top_by_position = calculate_top_players(all_players)

        # --- New Points Per Player Per Position ---
        
        # Helper for sorting players
        pos_order = ["QB", "RB", "WR", "TE", "FLEX", "D/ST", "K", "P"]
        def get_player_sort_key(player):
            slot = player['slot_position']
            if slot == 'BE':
                return (1, 0) # Bench players last
            try:
                return (0, pos_order.index(slot))
            except ValueError:
                return (0, len(pos_order)) # Other starters after defined order

        # Group players by team
        players_by_team = {}
        # Create a mapping from team_name to the actual Team object for easy lookup
        team_name_to_object = {team.team_name: team for team in self.data.league.teams}

        for player in all_players:
            if player['team_abbrev'] != 'FA':
                team_name = player['team_name']
                if team_name not in players_by_team:
                    players_by_team[team_name] = {
                        'team_object': team_name_to_object.get(team_name), # Add the Team object here
                        'players': [],
                        'grouped_points_breakdown': {},
                        'detailed_points_breakdown': []
                    }
                players_by_team[team_name]['players'].append(player)

        # Process stats for each player and sort
        stat_name_to_id_map = {v: int(k) for k, v in PLAYER_STATS_MAP.items()}
        for team_name, team_data in players_by_team.items():
            for player in team_data['players']:
                # Normalize stats table
                actual_breakdown = player.get('points_breakdown') or {}
                proj_breakdown = player.get('projected_points_breakdown') or {}
                
                all_stat_names = set(actual_breakdown.keys()) | set(proj_breakdown.keys())
                
                stat_ids = [stat_name_to_id_map.get(name) for name in all_stat_names if stat_name_to_id_map.get(name) is not None]
                
                # Create a list of stat info objects to sort by abbr
                stats_to_display = []
                for stat_id in stat_ids:
                    stat_name = PLAYER_STATS_MAP.get(stat_id)
                    header_info = SETTINGS_SCORING_FORMAT_MAP.get(stat_id, {})
                    stats_to_display.append({
                        'id': stat_id,
                        'name': stat_name,
                        'abbr': header_info.get('abbr', stat_name or str(stat_id)),
                        'label': header_info.get('label', stat_name or str(stat_id))
                    })
                
                stats_to_display.sort(key=lambda x: x['abbr'])

                headers = []
                actual_row = []
                proj_row = []

                for stat_info in stats_to_display:
                    stat_name = stat_info['name']
                    
                    headers.append({
                        'abbr': stat_info['abbr'],
                        'label': stat_info['label']
                    })
                    
                    actual_pts = actual_breakdown.get(stat_name, 0.0)
                    proj_pts = proj_breakdown.get(stat_name, 0.0)
                    
                    actual_style = ''
                    proj_style = ''
                    if actual_pts == proj_pts:
                        actual_style = 'light-blue'
                        proj_style = 'light-blue'
                    elif actual_pts > proj_pts:
                        actual_style = 'light-green'
                    else:
                        proj_style = 'light-red'
                    
                    actual_row.append({'value': actual_pts, 'style': actual_style})
                    proj_row.append({'value': proj_pts, 'style': proj_style})

                player['stats_table'] = {
                    'headers': headers,
                    'actual': actual_row,
                    'projected': proj_row
                }

            team_data['players'].sort(key=get_player_sort_key)

        # Calculate team-specific points breakdowns
        for team_name, team_data in players_by_team.items():
            team_all_players = team_data['players']
            team_aggregated_points_by_id = {}

            for player in team_all_players:
                if player["slot_position"] == "BE": # Only consider starters for team breakdown
                    continue
                if "points_breakdown" in player and player["points_breakdown"]:
                    for stat_name, points in player["points_breakdown"].items():
                        if isinstance(stat_name, str) and isinstance(points, (int, float)):
                            stat_id = stat_name_to_id_map.get(stat_name)
                            if stat_id:
                                team_aggregated_points_by_id[stat_id] = team_aggregated_points_by_id.get(stat_id, 0.0) + points

            team_detailed_points_breakdown = []
            for stat_id, total_points in team_aggregated_points_by_id.items():
                stat_name = PLAYER_STATS_MAP.get(int(stat_id))
                category = STAT_CATEGORY_LOOKUP.get(stat_name, "Other") if stat_name else "Other"
                try:
                    label = SETTINGS_SCORING_FORMAT_MAP.get(int(stat_id), {}).get('label', stat_name or stat_id)
                except (ValueError, TypeError):
                    label = stat_name or stat_id

                team_detailed_points_breakdown.append({
                    'label': label,
                    'category': category,
                    'total_points': total_points
                })

            team_detailed_points_breakdown.sort(key=lambda x: (x['category'], x['label']))

            team_grouped_points_breakdown = {}
            for item in team_detailed_points_breakdown:
                category = item['category']
                team_grouped_points_breakdown[category] = team_grouped_points_breakdown.get(category, 0.0) + item['total_points']

            team_data['grouped_points_breakdown'] = dict(sorted(team_grouped_points_breakdown.items()))
            team_data['detailed_points_breakdown'] = team_detailed_points_breakdown

        # Prepare data for radar charts
        all_stat_categories = set()
        for team_name, team_data in players_by_team.items():
            all_stat_categories.update(team_data['grouped_points_breakdown'].keys())
        
        sorted_stat_categories = sorted(list(all_stat_categories))

        for team_name, team_data in players_by_team.items():
            team_points_data = []
            for category in sorted_stat_categories:
                team_points_data.append(team_data['grouped_points_breakdown'].get(category, 0.0))
            
            team_data['radar_chart_data'] = {
                'labels': sorted_stat_categories,
                'datasets': [{
                    'label': team_name,
                    'data': team_points_data
                }]
            }

        # Prepare template context
        context = {
            "year": self.year,
            "week": week,
            "matchups": matchups,
            "weekly_scores": weekly_scores,
            "players_by_team": players_by_team, # New data structure
            "standings": self.data.get_standings(),
            "power_rankings": self.data.get_power_rankings(week),
            "top_week": self.data.get_top_scored_week(),
            "low_week": self.data.get_least_scored_week(),
            "top_scorer": self.data.get_top_scorer(),
            "low_scorer": self.data.get_least_scorer(),
            "most_pa": self.data.get_most_points_against(),
            "top_overall_players": top_overall,
            "top_players_by_position": top_by_position,
            "largest_weekly_margin": largest_weekly_margin,
            "largest_season_margin": largest_season_margin,
        }

        # --- Points Breakdown Refactored ---

        # Aggregate points by stat ID
        stat_name_to_id_map = {v: k for k, v in PLAYER_STATS_MAP.items()}
        aggregated_points_by_id = {}
        for player in all_players:
            if player["slot_position"] == "QB":
                print(player)
            if player["team_abbrev"] == "FA" or player["slot_position"] == "BE":
                continue
            if "points_breakdown" in player and player["points_breakdown"]:
                for stat_name, points in player["points_breakdown"].items():
                    if isinstance(stat_name, str) and isinstance(points, (int, float)):
                        stat_id = stat_name_to_id_map.get(stat_name)
                        if stat_id:
                            aggregated_points_by_id[stat_id] = aggregated_points_by_id.get(stat_id, 0.0) + points

        # Create detailed breakdown with all necessary info
        detailed_points_breakdown = []
        for stat_id, total_points in aggregated_points_by_id.items():
            # PLAYER_STATS_MAP is {id: name}, but id is a string. Let's be safe.
            stat_name = PLAYER_STATS_MAP.get(int(stat_id))
            category = STAT_CATEGORY_LOOKUP.get(stat_name, "Other") if stat_name else "Other"

            # SETTINGS_SCORING_FORMAT_MAP is {id: object}, id is an int.
            # Let's ensure we handle string/int keys properly.
            try:
                label = SETTINGS_SCORING_FORMAT_MAP.get(int(stat_id), {}).get('label', stat_name or stat_id)
            except (ValueError, TypeError):
                label = stat_name or stat_id

            detailed_points_breakdown.append({
                'label': label,
                'category': category,
                'total_points': total_points
            })

        # Sort by category, then by label
        detailed_points_breakdown.sort(key=lambda x: (x['category'], x['label']))

        # Create grouped breakdown for the pie chart
        grouped_points_breakdown = {}
        for item in detailed_points_breakdown:
            category = item['category']
            grouped_points_breakdown[category] = grouped_points_breakdown.get(category, 0.0) + item['total_points']

        # Sort the grouped data by category for consistent display
        sorted_grouped_points_breakdown = dict(sorted(grouped_points_breakdown.items()))

        # Prepare data for radar chart
        all_stat_categories = set()
        for team_name, team_data in players_by_team.items():
            all_stat_categories.update(team_data['grouped_points_breakdown'].keys())
        
        sorted_stat_categories = sorted(list(all_stat_categories))

        radar_datasets = []
        for team_name, team_data in players_by_team.items():
            team_points_data = []
            for category in sorted_stat_categories:
                team_points_data.append(team_data['grouped_points_breakdown'].get(category, 0.0))
            
            radar_datasets.append({
                'label': team_name,
                'data': team_points_data
            })
        
        final_radar_chart_data = {
            'labels': sorted_stat_categories,
            'datasets': radar_datasets
        }

        # Add to context
        context["grouped_points_breakdown"] = sorted_grouped_points_breakdown
        context["detailed_points_breakdown"] = detailed_points_breakdown
        context["radar_chart_data"] = final_radar_chart_data # Use the new structure

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
