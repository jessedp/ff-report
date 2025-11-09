# Project Overview

This project is a Python command-line tool for generating fantasy football reports for ESPN leagues. It provides weekly reports with detailed statistics, box scores, league standings, and power rankings.

**Key Technologies:**

- **Python:** The core language for the application.
- **uv:** used to Python package and project manager,
- **ESPN API:** Uses the `espn-api` library to fetch data from ESPN's fantasy football platform.
- **LLM Integration:** Uses OpenAI or Gemini models to generate narrative summaries of the week's events.
- **Jinja2:** For templating the HTML reports.
- **Click:** For creating the command-line interface.
- **python-dotenv:** For managing environment variables for configuration.

**Architecture:**

- The main application logic is contained within the `ff` package.
- `ff/__main__.py`: The entry point for the CLI, defining the available commands and options.
- `ff/config.py`: Handles configuration, including loading credentials from a `.env` file.
- `ff/data.py`: Encapsulates data retrieval from the ESPN API.
- `ff/reports.py`: Contains the logic for generating the reports.
- `ff/llm_report.py`: Gathers data and uses an LLM to generate a weekly summary.
- `ff/stats.py`: Performs statistical calculations.
- `templates/`: Contains the Jinja2 HTML templates for the reports.
- `build.sh`: Unified script for building the project for deployment and for generating local previews.

# Building and Running

**1. Installation:**

Install the project and its dependencies using pip:

```bash
pip install -e .
```

**2. Configuration:**

Create a `.env` file in the project root (you can copy `.env.example`) and add your ESPN API credentials. You will also need to add an API key for either OpenAI (`OPENAI_API_KEY`) or Google Gemini (`GOOGLE_GEMINI_API_KEY`) to use the LLM summary feature.

**3. Running the Application:**

The primary way to run the application is through the `ff` command-line interface.

**Generate a weekly report:**

```bash
ff weekly
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

.PHONY: build deploy dry-run clean preview

# Build the project for deployment
build:
	./build.sh build

# Preview a weekly report
# Usage: make preview WEEK=3
preview:
	@if [ -z "$(WEEK)" ]; then \
		echo "Please specify a week, e.g., make preview WEEK=3"; \
		exit 1;
	fi
	./build.sh --week $(WEEK)

# Deploy the built dist/ to the remote server
deploy:
	rsync -avz --quiet --delete --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fgo=r  dist/ ls2:/var/www/tbol/ff/

# Dry-run to see what would be deployed without actually doing it
dry-run:
	rsync -avz --delete --dry-run --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fgo=r  dist/ ls2:/var/www/tbol/ff/

# Clean up the dist/ directory
clean:
	rm -rf dist/
```

- `make build`: Runs the unified build script to create a production-ready build in the `dist/` directory.
- `make preview WEEK=<N>`: Generates a preview for a specific week and starts a local web server.
- `make deploy`: Deploys the contents of the `dist/` directory to the production server.
- `make dry-run`: Shows which files would be deployed without actually making any changes.
- `make clean`: Deletes the `dist/` directory.

# Development Conventions

- **Code Style:** The project follows standard Python coding conventions.
- **Testing:** (TODO: Add information about testing practices if tests are found.)
- **Contributions:** (TODO: Add information about contribution guidelines if available.)
- **Dependencies:** Project dependencies are managed in `setup.py`.

# Session Summary (Tuesday, September 16, 2025)

This session focused on refactoring the build process and improving documentation.

### Key Accomplishments:

1.  **Build Script Unification:**

    - Refactored the separate `build.sh` and `preview.sh` scripts into a single, unified `build.sh` script.
    - The new script defaults to a `preview` mode and accepts a `build` argument for creating production builds, reducing code duplication and improving maintainability.

2.  **Makefile Update:**

    - Updated the `Makefile` to work with the new `build.sh` script.
    - The `build` target now correctly calls `./build.sh build`.
    - A new `preview` target was added (`make preview WEEK=<N>`) for easier local previews.

3.  **LLM Report Path Consolidation:**

    - Modified `ff/llm_report.py` to save generated summary reports to a single, consistent directory: `reports/llm_summary/`.
    - Updated the build and preview logic to source summary reports from this new location.

4.  **Documentation Update:**
    - Updated `README.md` and `GEMINI.md` to reflect the new build process, project structure, and LLM-related features.

# Session Summary (Sunday, September 14, 2025)

This session focused on significant enhancements to the weekly report generation, particularly around data visualization and detailed breakdowns.

### Key Accomplishments:

1.  **`preview.sh` Script Improvement:**

    - Modified the script to check for an existing server on port 8000 before attempting to start a new one, preventing errors and redundant processes.

2.  **Interactive Points Breakdown Chart:**

    - Replaced the static "Aggregated Points Breakdown" table with an interactive doughnut chart.
    - Implemented functionality where clicking on a chart slice _or_ its corresponding legend item reveals a new bar chart.
    - The bar chart details the specific stat categories that make up the selected doughnut slice.
    - The color of the bar chart is synchronized with the color of the clicked doughnut slice for better visual context.
    - A custom, self-contained `transparentize` JavaScript function was created to generate prettier, semi-transparent colors for the charts without adding external libraries.

3.  **"Points Per Player Breakdown" Section Overhaul:**

    - Completely redesigned the layout and data presentation for this section.
    - Data is now grouped by fantasy team and separated into "Starters" and "Bench".
    - Starters are sorted in a logical position order (`QB, RB, WR,` etc.).
    - Each player entry now displays:
      - The player's info and pro team logo.
      - A summary of total points in "ACT / proj" format, with a larger font for the actual points.
      - A detailed, horizontally scrollable table breaking down points by individual stat.
    - **Stats Table Features:**
      - **Actual vs. Projected:** The table has dedicated rows for both actual and projected points.
      - **Column Normalization:** All available stat categories from both actual and projected breakdowns are included, ensuring columns are always aligned.
      - **Conditional Formatting:** Cells are color-coded (green for over-performance, red for under-performance, blue for meeting projection) to provide at-a-glance analysis.
      - **Sorted Headers:** The table columns are now sorted alphabetically by the stat abbreviation (e.g., 'PA', 'PC', 'PY').

4.  **Backend & Styling Refinements:**
    - **Data Layer:** Updated `ff/data.py` to fetch `projected_points` and `projected_points_breakdown` from the API.
    - **Data Processing:** Significantly refactored `ff/reports.py` to handle the complex normalization, sorting, and styling logic for the new player breakdown tables, passing a clean, pre-processed data structure to the template.
    - **CSS:** Added multiple new CSS classes to `templates/base.jinja` to support the new layouts, colors, and responsive scrolling.
