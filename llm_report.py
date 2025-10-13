"""
This script gathers fantasy football data, formats it, and uses an LLM to generate a report.
"""

import os
import re
import glob
import logging
import time
import datetime
import argparse
import shutil
from dotenv import load_dotenv
import openai
import google.generativeai as genai
from ff.game_summary import generate_summary, generate_simplified_summary
from ff.data import LeagueData
from ff.config import LEAGUE_YEAR

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- LLM Provider Abstraction ---

class LLMProvider:
    """Abstract base class for LLM providers."""
    def generate_report(self, prompt_data: dict) -> str:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """An implementation of LLMProvider for OpenAI models."""
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate_report(self, prompt_data: dict) -> str:
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
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = model

    def generate_report(self, prompt_data: dict) -> str:
        logging.info("Gemini API call is enabled.")
        system_prompt = prompt_data.get("system", "You are a helpful assistant.")
        user_content = (
            f"## Current Week Data\n\n{prompt_data.get('current', '')}\n\n"
            f"## Historical Data\n\n{prompt_data.get('historical', '')}"
        )
        messages = [
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["Okay, I understand. How can I help?"]},
            {"role": "user", "parts": [user_content]},
        ]
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(messages)
            return response.text
        except Exception as e:
            return f"Error generating report from Gemini: {e}"

# --- Data Gathering Functions ---

def get_system_prompt(filepath: str) -> str:
    try:
        with open(filepath, "r") as f:
            prompt = f.read()
        prompt = re.sub(r"Data: \[.*?\]", "", prompt).strip()
        return prompt
    except FileNotFoundError:
        return "You are a helpful fantasy football assistant."

def get_historical_data(year: int, week: int) -> str:
    historical_content = []
    simplified_reports_dir = "reports/simplified"
    os.makedirs(simplified_reports_dir, exist_ok=True)
    league_data_cache = {}
    all_report_html_files = glob.glob("reports/*-week*.html")
    all_historical_weeks = set()
    for html_file in all_report_html_files:
        basename = os.path.basename(html_file)
        match = re.search(r"(\d{4})-week(\d+)\.html", basename)
        if match:
            file_year, file_week = int(match.group(1)), int(match.group(2))
            all_historical_weeks.add((file_year, file_week))
    sorted_historical_weeks = sorted(list(all_historical_weeks))
    for file_year, file_week in sorted_historical_weeks:
        if file_year < year or (file_year == year and file_week < week):
            simplified_filename = f"{file_year}-week{file_week}.md"
            simplified_filepath = os.path.join(
                simplified_reports_dir, simplified_filename
            )
            if os.path.exists(simplified_filepath):
                with open(simplified_filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                if file_year not in league_data_cache:
                    logging.info(f"Initializing LeagueData for year {file_year}...")
                    start_time = time.time()
                    league_data_cache[file_year] = LeagueData(year=file_year)
                    end_time = time.time()
                    logging.info(
                        f"LeagueData for {file_year} initialized in {end_time - start_time:.2f} seconds."
                    )
                current_year_league_data = league_data_cache[file_year]
                content = generate_simplified_summary(
                    file_week, file_year, current_year_league_data
                )
                with open(simplified_filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            header = f"---Data from {simplified_filename} ---

"
            historical_content.append(header + content)
    return (
        "\n\n".join(historical_content)
        if historical_content
        else "No historical data found."
    )

def create_llm_report(week: int, year: int, provider: LLMProvider) -> str:
    system_prompt = get_system_prompt("prompt.txt")
    current_data = generate_summary(week)
    historical_data = get_historical_data(year, week)
    prompt_data = {
        "system": system_prompt,
        "current": current_data,
        "historical": historical_data,
    }
    report = provider.generate_report(prompt_data)
    return report

def main(week: int, year: int, llm_provider_name: str, force: bool, preview: bool):
    load_dotenv()
    provider_instance = None
    if llm_provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in .env file.")
            return
        provider_instance = OpenAIProvider(api_key=api_key)
    elif llm_provider_name == "gemini":
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            print("Error: GOOGLE_GEMINI_API_KEY not found in .env file.")
            return
        provider_instance = GeminiProvider(api_key=api_key)
    else:
        print(f"Error: Unknown LLM provider '{llm_provider_name}'. Choose 'openai' or 'gemini'.")
        return

    print(f"Gathering data for week {week}, {year} and generating LLM report using {llm_provider_name}...")
    llm_report = create_llm_report(week, year, provider_instance)

    if preview:
        print("\n--- Generated LLM Report (Preview) ---")
        print(llm_report)
        return

    summary_dir = "reports/llm_summary"
    os.makedirs(summary_dir, exist_ok=True)
    report_filename = f"{year}-week{week}_llm_summary.md"
    report_path = os.path.join(summary_dir, report_filename)

    if os.path.exists(report_path):
        if force:
            backup_path = f"{report_path}.bk"
            shutil.move(report_path, backup_path)
            logging.info(f"Backed up existing report to {backup_path}")
        else:
            logging.info(f"Report {report_path} already exists. Use --force to overwrite.")
            return

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(llm_report)
    logging.info(f"LLM report saved to {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an LLM-powered fantasy football report.")
    parser.add_argument("--week", type=int, required=True, help="The NFL week for the report.")
    parser.add_argument("--year", type=int, default=LEAGUE_YEAR, help=f"The NFL season year for the report (default: {LEAGUE_YEAR}).")
    parser.add_argument("--llm-provider", type=str, default="openai", choices=["openai", "gemini"], help="The LLM provider to use.")
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing report by creating a backup.")
    parser.add_argument("--preview", action="store_true", help="Print the report to the console without saving to a file.")
    args = parser.parse_args()
    main(week=args.week, year=args.year, llm_provider_name=args.llm_provider, force=args.force, preview=args.preview)
