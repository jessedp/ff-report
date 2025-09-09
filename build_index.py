
import os
import json
import re

REPORTS_DIR = 'reports'
OUTPUT_FILE = 'reports.json'

def build_index():
    reports = {}
    if not os.path.exists(REPORTS_DIR):
        print(f"Directory not found: {REPORTS_DIR}")
        return

    for filename in os.listdir(REPORTS_DIR):
        match = re.match(r'(\d{4})-week(\d+)\.html', filename)
        if match:
            year, week = match.groups()
            year = int(year)
            week = int(week)
            if year not in reports:
                reports[year] = []
            reports[year].append(week)

    for year in reports:
        reports[year].sort()

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(reports, f, indent=4, sort_keys=True)

    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    build_index()
