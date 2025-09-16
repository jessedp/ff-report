"""Fantasy Football CLI application"""
import os
import subprocess
import click
from .reports import WeeklyReport
from .config import LEAGUE_YEAR, DEFAULT_WEEK
from .data import LeagueData
from .game_summary import generate_summary

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
              help='Output file path (defaults to reports/YEAR-weekWEEK.html)')
@click.option('--open', '-p', is_flag=True, default=False,
              help='Open the report in a browser after generation')
@click.option('--force', '-f', is_flag=True, default=False,
              help='Force overwrite of existing report')
def weekly(year, week, output, open, force):
    """Generate a weekly fantasy football report."""
    report = WeeklyReport(year=year)

    # Use current week if week is 0
    effective_week = week
    if effective_week == 0:
        effective_week = report.data.get_current_week()

    # Determine output file path
    if output is None:
        output_dir = "reports"
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, f"{year}-week{effective_week}.html")
    else:
        output_file_path = output

    # Check if file exists and if it's not the current report
    if os.path.exists(output_file_path) and not force:
        current_year = LEAGUE_YEAR
        # Assuming LeagueData() gets the current year's data
        current_week = LeagueData().get_current_week()
        is_current_report = (year == current_year and effective_week == current_week)

        if not is_current_report:
            click.echo(f"Error: {output_file_path} already exists. Use --force to overwrite.")
            return

    # The generate function now correctly handles the output path
    generated_file = report.generate(week=week if week != 0 else None, output_file=output)
    click.echo(f"Report generated: {generated_file}")

    if open:
        # Try to open the file in the default browser
        try:
            if os.path.exists('./xdg-open'):
                subprocess.run(['./xdg-open', generated_file])
            elif os.name == 'nt':  # Windows
                os.startfile(generated_file)
            elif os.name == 'posix':  # macOS or Linux
                if os.path.exists('/usr/bin/open'):  # macOS
                    subprocess.run(['open', generated_file])
                else:  # Linux
                    subprocess.run(['xdg-open', generated_file])
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

    for week_num in range(start, end + 1):
        try:
            # We can reuse the logic from the weekly command, but without forcing
            output_dir = "reports"
            output_file = os.path.join(output_dir, f"{year}-week{week_num}.html")
            if os.path.exists(output_file):
                click.echo(f"Skipping existing report: {output_file}")
                continue

            generated_file = report.generate(week=week_num)
            click.echo(f"Generated report for Week {week_num}: {generated_file}")
        except Exception as e:
            click.echo(f"Error generating report for Week {week_num}: {e}")

@cli.command()
@click.option('--week', '-w', type=int, default=DEFAULT_WEEK,
                help='NFL week to generate summary for (0 for current week)')
def summary(week):
    """Generate a game summary for a given week."""
    # Use current week if week is 0
    effective_week = week
    if effective_week == 0:
        effective_week = LeagueData().get_current_week()

    summary_text = generate_summary(effective_week)
    click.echo(summary_text)

if __name__ == '__main__':
    cli()
