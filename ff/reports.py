"""Generate fantasy football reports"""
import os
import hashlib
import urllib.request
import shutil
from .data import LeagueData
from .stats import calculate_weekly_scores, calculate_matchups, points_per_player_per_position
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

    # Handle specific URL redirects
    if 'practicalhorsemanmag.com/.image/t_share/' in logo_url:
        filename = logo_url.split('/')[-1]
        logo_url = f'https://practicalhorsemanmag.com/wp-content/uploads/migrations/practicalhorseman/{filename}'

    # Create a unique filename from the URL
    url_hash = hashlib.md5(logo_url.encode('utf-8')).hexdigest()
    file_extension = os.path.splitext(logo_url)[1]
    if '_dark' in file_extension:
        file_extension = file_extension.replace('_dark', '')
    if '?' in file_extension:
        file_extension = file_extension.split('?')[0]
    if not file_extension:
        file_extension = '.png'

    filename = f"{url_hash}{file_extension}"
    cache_dir = "cache/images"
    os.makedirs(cache_dir, exist_ok=True)
    local_path = os.path.join(cache_dir, filename)

    # Download if it doesn't exist
    if not os.path.exists(local_path):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://fantasy.espn.com/',
                'Accept': '*/*',
                'Cookie': f'swid={SWID}; espn_s2={ESPN_S2};'
            }
            req = urllib.request.Request(logo_url, headers=headers)
            with urllib.request.urlopen(req) as response, open(local_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(f"Error downloading logo: {logo_url} - {e}")
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
        weekly_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # --- Logo Caching ---
        for matchup in matchups:
            matchup['home_team']['logo'] = cache_logo(matchup['home_team']['logo'])
            matchup['away_team']['logo'] = cache_logo(matchup['away_team']['logo'])

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
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{self.year}-week{week}.html")
        
        # Write the HTML to the file
        with open(output_file, 'w') as f:
            f.write(html)
        
        return output_file