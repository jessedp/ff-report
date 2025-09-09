from espn_api.football import League
from .config import LEAGUE_ID, LEAGUE_YEAR, SWID, ESPN_S2


class LeagueData:
    """Handles ESPN API data retrieval and caching"""

    def __init__(self, year=LEAGUE_YEAR):
        """Initialize the league data handler

        Args:
            year: The NFL season year to fetch data for
        """
        self.year = year
        self.league = League(
            league_id=LEAGUE_ID,
            year=int(year),
            swid=SWID,
            espn_s2=ESPN_S2,
        )

    def get_current_week(self):
        """Get the current fantasy football week"""
        return self.league.current_week

    def set_week(self, week):
        """Set the week for data retrieval

        Args:
            week: The week number to set
        """
        self.league.current_week = week

    def get_box_scores(self, week=None):
        """Get box scores for the specified week

        Args:
            week: Week number to get scores for (uses current week if None)

        Returns:
            List of box score objects
        """
        if week is not None:
            return self.league.box_scores(week)
        return self.league.box_scores()

    def get_power_rankings(self, week=None):
        """Get power rankings for the specified week

        Args:
            week: Week number to get rankings for (uses current week if None)

        Returns:
            List of power ranking tuples (score, team)
        """
        if week is not None:
            return self.league.power_rankings(week)
        return self.league.power_rankings()

    def get_standings(self):
        """Get league standings

        Returns:
            List of teams sorted by standings
        """
        return self.league.standings()

    def get_top_scored_week(self):
        """Get the highest scoring week in the league

        Returns:
            Tuple of (team, score)
        """
        return self.league.top_scored_week()

    def get_least_scored_week(self):
        """Get the lowest scoring week in the league

        Returns:
            Tuple of (team, score)
        """
        return self.league.least_scored_week()

    def get_top_scorer(self):
        """Get the top scoring team for the season

        Returns:
            Team object
        """
        return self.league.top_scorer()

    def get_least_scorer(self):
        """Get the lowest scoring team for the season

        Returns:
            Team object
        """
        return self.league.least_scorer()

    def get_most_points_against(self):
        """Get the team with the most points scored against them

        Returns:
            Team object
        """
        return self.league.most_points_against()

    def get_weekly_players(self, week=None):
        """Get all players and their scores for a given week

        Args:
            week: The week number to get players for

        Returns:
            A list of player dictionaries
        """
        if week is None:
            week = self.get_current_week()

        box_scores = self.get_box_scores(week)
        free_agents = self.league.free_agents(week=week, size=50)

        all_players = []

        # Get players from team lineups
        for matchup in box_scores:
            for player in matchup.home_lineup:
                all_players.append(
                    {
                        "name": player.name,
                        "points": player.points,
                        "position": player.position,
                        "slot_position": player.slot_position,
                        "pro_team": player.proTeam,
                        "team_name": matchup.home_team.team_name,
                        "team_abbrev": matchup.home_team.team_abbrev,
                        "team_logo": matchup.home_team.logo_url,
                    }
                )
            for player in matchup.away_lineup:
                all_players.append(
                    {
                        "name": player.name,
                        "points": player.points,
                        "position": player.position,
                        "slot_position": player.slot_position,
                        "pro_team": player.proTeam,
                        "team_name": matchup.away_team.team_name,
                        "team_abbrev": matchup.away_team.team_abbrev,
                        "team_logo": matchup.away_team.logo_url,
                    }
                )

        # Get free agents
        for player in free_agents:
            all_players.append(
                {
                    "name": player.name,
                    "points": player.points,
                    "position": player.position,
                    "slot_position": "FA",
                    "pro_team": player.proTeam,
                    "team_name": "Free Agent",
                    "team_abbrev": "FA",
                    "team_logo": "images/logo_svg/NFL.svg",
                }
            )

        return all_players