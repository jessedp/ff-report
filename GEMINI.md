# Project Overview

This project is a Python command-line tool for generating fantasy football reports for ESPN leagues. It provides weekly reports with detailed statistics, box scores, league standings, and power rankings.

**Key Technologies:**

*   **Python:** The core language for the application.
*   **ESPN API:** Uses the `espn-api` library to fetch data from ESPN's fantasy football platform.
We are using the the espn-api python package. I've cloned the documentation wiki into docs/
docs/espn-api.wiki/Football-Intro.md
docs/espn-api.wiki/Box-Player-Class.md
docs/espn-api.wiki/Player-Class.md
docs/espn-api.wiki/League-Class.md
docs/espn-api.wiki/Matchup-Class.md
docs/espn-api.wiki/Team-Class.md


*   **Jinja2:** For templating the HTML reports.
*   **Click:** For creating the command-line interface.
*   **python-dotenv:** For managing environment variables for configuration.

**Architecture:**

*   The main application logic is contained within the `ff` package.
*   `ff/__main__.py`: The entry point for the CLI, defining the available commands and options.
*   `ff/config.py`: Handles configuration, including loading credentials from a `.env` file.
*   `ff/data.py`: Encapsulates data retrieval from the ESPN API.
*   `ff/reports.py`: Contains the logic for generating the reports.
*   `ff/stats.py`: Performs statistical calculations.
*   `templates/`: Contains the Jinja2 HTML templates for the reports.

# Building and Running

**1. Installation:**

Install the project and its dependencies using pip:

```bash
pip install -e .
```

**2. Configuration:**

Create a `.env` file in the project root (you can copy `.env.example`) and add your ESPN API credentials.

**3. Running the Application:**

The primary way to run the application is through the `ff` command-line interface.

**Generate a weekly report:**

```bash
ff weekly --open
```

**Generate a report for a specific week:**

```bash
ff weekly --week 5 --open
```

**Generate reports for a range of weeks:**

```bash
ff generate-all --start 1 --end 17
```

A convenience script, `run.sh`, is also provided to generate the current week's report.

```bash
./run.sh
```

# Makefile

The project includes a `Makefile` for common development tasks:

```makefile
# Makefile for Fantasy Football App

.PHONY: build deploy dry-run

# Build the project by running the build script
build:
	./build.sh

# Deploy the built dist/ to the remote server
deploy:
	rsync -avz --delete dist/ ls2:/var/www/tbol/ff/

# Dry-run to see what would be deployed without actually doing it
dry-run:
	rsync -avz --delete --dry-run dist/ ls2:/var/www/tbol/ff/

# Clean up the dist/ directory
clean:
	rm -rf dist/
```

*   `make build`: Builds the report viewer and copies all necessary files to the `dist/` directory.
*   `make deploy`: Deploys the contents of the `dist/` directory to the production server.
*   `make dry-run`: Shows which files would be deployed without actually making any changes.
*   `make clean`: Deletes the `dist/` directory.

# Development Conventions

*   **Code Style:** The project follows standard Python coding conventions.
*   **Testing:** (TODO: Add information about testing practices if tests are found.)
*   **Contributions:** (TODO: Add information about contribution guidelines if available.)
*   **Dependencies:** Project dependencies are managed in `setup.py`.
