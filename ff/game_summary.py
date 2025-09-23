"""
Generate fantasy football game summaries.

This script uses the espn-api library to fetch game data for a given week
and generate a markdown summary of each matchup.

The main data object is the `League` class from `espn_api.football`,
which provides access to teams, settings, scores, and more.
See docs/espn-api.wiki/League-Class.md for more details.
"""

import logging  # Added logging
import time  # Added time for timing
from .data import LeagueData
from espn_api.football.constant import SETTINGS_SCORING_FORMAT_MAP, PLAYER_STATS_MAP

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _format_player_summary(player):
    """Formats the summary for a single player."""
    summary = f"*   **{player.name}** ({player.slot_position}) - {player.points} points (proj: {player.projected_points})\n"

    game_date = getattr(player, "game_date", None)
    if game_date:
        summary += f"    *   **Game Date:** {game_date}\n"

    summary += f"    *   **Matchup:** {player.proTeam} vs {player.pro_opponent}\n"

    if player.points_breakdown:
        has_stats = False
        stats_summary = ""
        for stat, points in player.points_breakdown.items():
            if points == 0:
                continue

            has_stats = True
            stat_id = next((k for k, v in PLAYER_STATS_MAP.items() if v == stat), None)
            if stat_id:
                label = SETTINGS_SCORING_FORMAT_MAP.get(int(stat_id), {}).get(
                    "label", stat
                )
                stats_summary += f"        *   {label}: {round(points, 2)} points\n"

        if has_stats:
            summary += "    *   **Stats:**\n"
            summary += stats_summary
    return summary


def generate_summary(week):
    """Generate a game summary for a given week.

    Args:
        week: The week number to generate the summary for.

    Returns:
        A string containing the game summary.
    """
    league_data = LeagueData()
    box_scores = league_data.get_box_scores(week)

    summary = f"# Week {week} Game Summaries\n\n"

    # Add League Info section
    summary += "## League Information\n\n"
    try:
        # Standings
        standings = league_data.league.standings()
        summary += "### Standings\n\n"
        summary += "| Rank | Team | Record |\n"
        summary += "|:----:|:-----|:------:|\n"
        standings.sort(key=lambda x: x.standing)
        for team in standings:
            summary += f"| {team.standing} | {team.team_name} ({team.team_abbrev}) | {team.wins}-{team.losses} |\n"
        summary += "\n"

        # Settings
        summary += "### Settings\n\n"
        settings = league_data.league.settings
        summary += f"- **League Name:** {settings.name}\n"
        summary += f"- **Number of Teams:** {len(league_data.league.teams)}\n"

        if settings.division_map:
            summary += "- **Divisions:**\n"
            for division_id, division_name in settings.division_map.items():
                summary += f"  - {division_name}\n"
        summary += "\n"

    except Exception as e:
        summary += (
            f"<p><em>Could not retrieve league information. Error: {e}</em></p>\n\n"
        )

    summary += "## Matchup Summaries\n\n"

    for matchup in box_scores:
        summary += f"### {matchup.home_team.team_name} ({matchup.home_team.team_abbrev}) vs. {matchup.away_team.team_name} ({matchup.away_team.team_abbrev})\n\n"
        summary += f"**Final Score:** {matchup.home_score} - {matchup.away_score}\n\n"

        for team in [matchup.home_team, matchup.away_team]:
            summary += f"#### {team.team_name} ({team.team_abbrev})\n\n"

            lineup = (
                matchup.home_lineup
                if team == matchup.home_team
                else matchup.away_lineup
            )

            starters = [p for p in lineup if p.slot_position != "BE"]
            bench = [p for p in lineup if p.slot_position == "BE"]

            summary += "##### Starters\n\n"
            for player in starters:
                summary += _format_player_summary(player)
            summary += "\n"

            summary += "##### Bench\n\n"
            for player in bench:
                summary += _format_player_summary(player)
            summary += "\n"

    return summary


def generate_simplified_summary(
    week: int, year: int, league_data: LeagueData
) -> str:  # Added year parameter
    """Generate a simplified game summary for a given week, focusing on matchup results.

    Args:
        week: The week number to generate the summary for.
        year: The year of the league.
        league_data: An initialized LeagueData object for the relevant year.

    Returns:
        A string containing the simplified game summary.
    """
    start_time = time.time()  # Start timing
    logging.info(f"Fetching box scores for {year} Week {week}...")
    box_scores = league_data.get_box_scores(week)
    end_time = time.time()  # End timing
    logging.info(
        f"Fetched {len(box_scores)} box scores for {year} Week {week} in {end_time - start_time:.2f} seconds."
    )

    if not box_scores:
        logging.warning(
            f"No box scores found for {year} Week {week}. This might indicate an issue with LEAGUE_ID for this year."
        )
        return f"### {year} Week {week} Simplified Game Summary\n\nNo data available for this week.\n\n"

    summary = f"### {year} Week {week} Simplified Game Summary\n\n"  # Updated header

    # Check for playoff status and add prominent statement if true
    if box_scores and box_scores[0].is_playoff:
        summary += "**THIS IS A PLAYOFF WEEK!**\n\n"

    for matchup in box_scores:
        # Determine the winner based on scores
        if matchup.home_score > matchup.away_score:
            winner_team = matchup.home_team
            loser_team = matchup.away_team
            summary += f"- **{winner_team.team_name} ({winner_team.team_abbrev})** defeated **{loser_team.team_name} ({loser_team.team_abbrev})** with a score of {matchup.home_score} (proj: {matchup.home_projected:.2f}) - {matchup.away_score} (proj: {matchup.away_projected:.2f}).\n"
        elif matchup.away_score > matchup.home_score:
            winner_team = matchup.away_team
            loser_team = matchup.home_team
            summary += f"- **{winner_team.team_name} ({winner_team.team_abbrev})** defeated **{loser_team.team_name} ({loser_team.team_abbrev})** with a score of {matchup.home_score} (proj: {matchup.home_projected:.2f}) - {matchup.away_score} (proj: {matchup.away_projected:.2f}).\n"
        else:  # Tie
            summary += f"- **{matchup.home_team.team_name} ({matchup.home_team.team_abbrev})** tied with **{matchup.away_team.team_name} ({matchup.away_team.team_abbrev})** with a score of {matchup.home_score} (proj: {matchup.home_projected:.2f}) - {matchup.away_score} (proj: {matchup.away_projected:.2f}).\n"

        # Calculate bench score and compare to starters
        home_bench_score = sum(
            p.points for p in matchup.home_lineup if p.slot_position == "BE"
        )
        away_bench_score = sum(
            p.points for p in matchup.away_lineup if p.slot_position == "BE"
        )

        if home_bench_score > matchup.home_score:
            summary += f"  - {matchup.home_team.team_abbrev}'s bench ({home_bench_score:.2f}) outscored their starters ({matchup.home_score:.2f}). 🤡\n"
        if away_bench_score > matchup.away_score:
            summary += f"  - {matchup.away_team.team_abbrev}'s bench ({away_bench_score:.2f}) outscored their starters ({matchup.away_score:.2f}). 🤡\n"

    return summary
