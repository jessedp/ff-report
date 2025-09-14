import os
import json
import re
import sys

def build_index(reports_dir='reports', output_file='reports.json'):
    reports = {}
    if not os.path.exists(reports_dir):
        print(f"Directory not found: {reports_dir}")
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return

    for filename in os.listdir(reports_dir):
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

    # sort years
    sorted_reports = {k: reports[k] for k in sorted(reports, reverse=True)}

    with open(output_file, 'w') as f:
        json.dump(sorted_reports, f, indent=4)

    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        build_index(sys.argv[1], sys.argv[2])
    elif len(sys.argv) > 1:
        build_index(reports_dir=sys.argv[1])
    else:
        build_index()