"""Generate fantasy football reports"""
import os
from .data import LeagueData
from .stats import calculate_weekly_scores, calculate_matchups, points_per_player_per_position
from .templates import TemplateEngine
from .config import LEAGUE_YEAR

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
        weekly_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Calculate position stats for all teams
        position_stats = {}
        for team in weekly_scores:
            position_stats[team['name']] = points_per_player_per_position(team['lineup'])
        
        # Prepare template context
        context = {
            'year': self.year,
            'week': week,
            'matchups': matchups,
            'weekly_scores': weekly_scores,
            'position_stats': position_stats,
            'standings': self.data.get_standings(),
            'power_rankings': self.data.get_power_rankings(week),
            'top_week': self.data.get_top_scored_week(),
            'low_week': self.data.get_least_scored_week(),
            'top_scorer': self.data.get_top_scorer(),
            'low_scorer': self.data.get_least_scorer(),
            'most_pa': self.data.get_most_points_against()
        }
        
        # Render the template
        html = self.template.render_weekly_report(context)
        
        # Determine output file path
        if output_file is None:
            output_file = f"{self.year}-week{week}.html"
        
        # Write the HTML to the file
        with open(output_file, 'w') as f:
            f.write(html)
        
        return output_file