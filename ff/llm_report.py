"""
This script gathers fantasy football data, formats it, and uses an LLM to generate a report.
"""

import os
import re
import glob
import logging  # Added logging
import time  # Added time for timing
import datetime  # Added datetime for timestamps
import argparse  # Added argparse
from dotenv import load_dotenv
import openai
from google import genai
from ff.game_summary import generate_summary, generate_simplified_summary
from ff.data import LeagueData
from ff.config import LEAGUE_YEAR

# Configure logging for llm_report.py
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- LLM Provider Abstraction ---


class LLMProvider:
    """Abstract base class for LLM providers."""

    def generate_report(self, prompt_data: dict) -> str:
        """Generates a report based on the provided prompt data."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """An implementation of LLMProvider for OpenAI models."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate_report(self, prompt_data: dict) -> str:
        """
        Generates a report using the OpenAI API.
        """
        logging.info("LLM API call is enabled.")

        system_prompt = prompt_data.get("system", "You are a helpful assistant.")
        user_content = (
            f"## Current Week Data\n\n{prompt_data.get('current', '')}\n\n"
            f"## Historical Data\n\n{prompt_data.get('historical', '')}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating report from OpenAI: {e}"


class GeminiProvider(LLMProvider):
    """An implementation of LLMProvider for Google Gemini models."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_report(self, prompt_data: dict) -> str:
        """
        Generates a report using the Google Gemini API.
        """
        logging.info("Gemini API call is enabled.")

        system_prompt = prompt_data.get("system", "You are a helpful assistant.")
        user_content = (
            f"## Current Week Data\n\n{prompt_data.get('current', '')}\n\n"
            f"## Historical Data\n\n{prompt_data.get('historical', '')}"
        )

        # The new API uses a different structure for messages
        contents = [
            system_prompt,
            "Okay, I understand. How can I help?",
            user_content,
        ]

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
            )
            return response.text
        except Exception as e:
            return f"Error generating report from Gemini: {e}"


# --- Data Gathering Functions ---


def get_system_prompt(filepath: str) -> str:
    """Reads the system prompt and removes the placeholder."""
    try:
        with open(filepath, "r") as f:
            prompt = f.read()
        # Remove the placeholder text
        prompt = re.sub(r"Data: \[.*?]", "", prompt).strip()
        return prompt
    except FileNotFoundError:
        return "You are a helpful fantasy football assistant."  # Fallback


def get_historical_data(year: int, week: int) -> str:
    """
    Gathers historical data from simplified markdown files, generating and caching them if needed.

    This function now uses simplified summaries to reduce token count.
    It reuses LeagueData objects per year to optimize API calls.
    """
    historical_content = []
    simplified_reports_dir = "reports/simplified"
    os.makedirs(simplified_reports_dir, exist_ok=True)

    # Cache LeagueData objects per year
    league_data_cache = {}

    all_report_html_files = glob.glob("reports/*-week*.html")

    # Extract all unique years and weeks from the HTML filenames
    all_historical_weeks = set()
    for html_file in all_report_html_files:
        basename = os.path.basename(html_file)
        match = re.search(r"(\d{4})-week(\d+)\.html", basename)
        if match:
            file_year, file_week = int(match.group(1)), int(match.group(2))
            all_historical_weeks.add((file_year, file_week))

    # Sort historical weeks
    sorted_historical_weeks = sorted(list(all_historical_weeks))

    for file_year, file_week in sorted_historical_weeks:
        # Only include files from previous years, or previous weeks of the current year
        if file_year < year or (file_year == year and file_week < week):
            simplified_filename = f"{file_year}-week{file_week}.md"
            simplified_filepath = os.path.join(
                simplified_reports_dir, simplified_filename
            )

            if os.path.exists(simplified_filepath):
                with open(simplified_filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                # Get LeagueData object for the current year from cache or create new
                if file_year not in league_data_cache:
                    logging.info(f"Initializing LeagueData for year {file_year}...")
                    start_time = time.time()
                    league_data_cache[file_year] = LeagueData(year=file_year)
                    end_time = time.time()
                    logging.info(
                        f"LeagueData for {file_year} initialized in {end_time - start_time:.2f} seconds."
                    )
                current_year_league_data = league_data_cache[file_year]

                # Generate simplified summary and cache it
                content = generate_simplified_summary(
                    file_week, file_year, current_year_league_data
                )  # Pass file_year
                with open(simplified_filepath, "w", encoding="utf-8") as f:
                    f.write(content)

            header = f"""---\nData from {simplified_filename} ---\n\n"""
            historical_content.append(header + content)

    return (
        "\n\n".join(historical_content)
        if historical_content
        else "No historical data found."
    )


def create_llm_report(week: int, year: int, provider: LLMProvider) -> str:
    """Generates a report from an LLM using game data."""
    # 1. Gather data
    system_prompt = get_system_prompt("prompt.txt")
    current_data = generate_summary(week)
    historical_data = get_historical_data(year, week)

    prompt_data = {
        "system": system_prompt,
        "current": current_data,
        "historical": historical_data,
    }

    # 2. Generate report from the provider
    report = provider.generate_report(prompt_data)
    return report


def main(week: int, year: int, llm_provider_name: str, force: bool, preview: bool):
    load_dotenv()

    provider_instance = None
    if llm_provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(
                "Error: OPENAI_API_KEY not found in .env file. Please create a .env file with your key."
            )
            return
        provider_instance = OpenAIProvider(api_key=api_key)
    elif llm_provider_name == "gemini":
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            print(
                "Error: GOOGLE_GEMINI_API_KEY not found in .env file. Please create a .env file with your key."
            )
            return
        provider_instance = GeminiProvider(api_key=api_key)
    else:
        print(
            f"Error: Unknown LLM provider '{llm_provider_name}'. Choose 'openai' or 'gemini'."
        )
        return

    print(
        f"Gathering data for week {week}, {year} and generating LLM report using {llm_provider_name}...\n"
    )

    llm_report = create_llm_report(week, year, provider_instance)

    print(
        "\n--- Generated LLM Report ---\
"
    )
    print(llm_report)

    # Save the report to file
    # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") # Removed timestamp
    report_filename_base = f"{year}-week{week}_llm_summary"

    # ./reports/llm_summary/YYYY-week(X)_llm_summary.md
    summary_dir = "reports/llm_summary"
    os.makedirs(summary_dir, exist_ok=True)
    report_path = os.path.join(summary_dir, f"{report_filename_base}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(llm_report)
    logging.info(f"LLM report saved to {report_path}")


# Example of how to run this script.
# You would typically call this from another script or a CLI command.
# For now, you can add a call here for testing, e.g.:
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an LLM-powered fantasy football report.")
    parser.add_argument("--week", type=int, required=True, help="The NFL week for the report.")
    parser.add_argument("--year", type=int, default=LEAGUE_YEAR, help=f"The NFL season year for the report (default: {LEAGUE_YEAR}).")
    parser.add_argument("--llm-provider", type=str, default="openai", choices=["openai", "gemini"], help="The LLM provider to use.")
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing report by creating a backup.")
    parser.add_argument("--preview", action="store_true", help="Print the report to the console without saving to a file.")
    args = parser.parse_args()
    main(week=args.week, year=args.year, llm_provider_name=args.llm_provider, force=args.force, preview=args.preview)
