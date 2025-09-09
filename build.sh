#!/bin/bash

# Exit on error
set -e

# Create the distribution directory
rm -rf dist
mkdir -p dist/reports

# Generate the reports index
python3 build_index.py
mv reports.json dist/

# Copy viewer files
cp viewer/index.html dist/
cp viewer/style.css dist/
cp viewer/app.js dist/

# Copy reports
if [ -d "reports" ] && [ "$(ls -A reports)" ]; then
    cp -r reports/* dist/reports/
fi

# Copy images directly into the reports directory
if [ -d "images" ] && [ "$(ls -A images)" ]; then
    cp -r images/* dist/reports/
fi

cp fball-16x16.png dist/reports/
cp fball-32x32.png dist/reports/
cp jag-16x16.png dist/reports/


# Copy cached images
if [ -d "cache/images" ] && [ "$(ls -A cache/images)" ]; then
    cp -r cache/images/* dist/reports/
fi


echo "Build complete. The 'dist' directory is ready for deployment."
