# Fantasy Football Reports

A cleaner, more maintainable fantasy football reporting tool for ESPN leagues.

## Requirements

- Python 3.9+

## Features

- Weekly reports with detailed statistics
- Box scores with analysis of bench scoring and "what could have been" scenarios
- League standings and power rankings
- Points per player per position analysis
- Clean HTML reports with consistent styling
- Easy to run from the command line

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -e .
   ```
3. Create a `.env` file with [your ESPN API credentials](https://github.com/cwendt94/espn-api/discussions/150#discussioncomment-133615) (use `.env.example` as a template)

## Usage

### Generate a report for the current week

```bash
# Using the run script
./run.sh

# Or using the CLI
ff weekly --open
```

### Generate a report for a specific week

```bash
ff weekly --week 10 --open
```

### Generate reports for multiple weeks

```bash
ff generate-all --start 1 --end 17
```

### CLI Options

```
Usage: ff [OPTIONS] COMMAND [ARGS]...

  Fantasy Football CLI application for generating reports and statistics.

Options:
  --help  Show this message and exit.

Commands:
  generate-all  Generate reports for all weeks in a range.
  weekly        Generate a weekly fantasy football report.
```

Weekly command options:

```
--year, -y INTEGER    NFL season year to generate report for
--week, -w INTEGER    NFL week to generate report for (0 for current week)
--output, -o TEXT     Output file path (defaults to YEAR-weekWEEK.html)
--open, -p            Open the report in a browser after generation
```

## Project Structure

- `ff/` - Main package directory
  - `__init__.py` - Package initialization
  - `__main__.py` - CLI entry point
  - `config.py` - Configuration handling
  - `data.py` - ESPN API data retrieval
  - `stats.py` - Statistical calculations
  - `reports.py` - Report generation
  - `templates.py` - HTML template handling
- `templates/` - Jinja2 HTML templates
- `run.sh` - Convenience script for running the application

## Customization

You can customize the report by:

1. Editing the Jinja2 templates in the `templates/` directory
2. Adjusting the CSS styles in the base template
3. Adding new statistical calculations to `stats.py`
4. Creating new report types in `reports.py`
