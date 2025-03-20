"""Fantasy Football CLI application"""
import os
import subprocess
import click
from .reports import WeeklyReport
from .config import LEAGUE_YEAR, DEFAULT_WEEK

@click.group()
def cli():
    """Fantasy Football CLI application for generating reports and statistics."""
    pass

@cli.command()
@click.option('--year', '-y', type=int, default=LEAGUE_YEAR, 
              help='NFL season year to generate report for')
@click.option('--week', '-w', type=int, default=DEFAULT_WEEK,
              help='NFL week to generate report for (0 for current week)')
@click.option('--output', '-o', type=str, default=None,
              help='Output file path (defaults to YEAR-weekWEEK.html)')
@click.option('--open', '-p', is_flag=True, default=False,
              help='Open the report in a browser after generation')
def weekly(year, week, output, open):
    """Generate a weekly fantasy football report."""
    report = WeeklyReport(year=year)
    
    # Use current week if week is 0
    if week == 0:
        week = None
        
    output_file = report.generate(week=week, output_file=output)
    click.echo(f"Report generated: {output_file}")
    
    if open:
        # Try to open the file in the default browser
        try:
            if os.path.exists('./xdg-open'):
                subprocess.run(['./xdg-open', output_file])
            elif os.name == 'nt':  # Windows
                os.startfile(output_file)
            elif os.name == 'posix':  # macOS or Linux
                if os.path.exists('/usr/bin/open'):  # macOS
                    subprocess.run(['open', output_file])
                else:  # Linux
                    subprocess.run(['xdg-open', output_file])
        except Exception as e:
            click.echo(f"Error opening report: {e}")

@cli.command()
@click.option('--year', '-y', type=int, default=LEAGUE_YEAR,
              help='NFL season year to generate reports for')
@click.option('--start', '-s', type=int, default=1,
              help='Starting week number')
@click.option('--end', '-e', type=int, default=17,
              help='Ending week number')
def generate_all(year, start, end):
    """Generate reports for all weeks in a range."""
    report = WeeklyReport(year=year)
    
    for week in range(start, end + 1):
        try:
            output_file = report.generate(week=week)
            click.echo(f"Generated report for Week {week}: {output_file}")
        except Exception as e:
            click.echo(f"Error generating report for Week {week}: {e}")

if __name__ == '__main__':
    cli()