# Makefile for Fantasy Football App

.PHONY: build deploy dry-run clean preview llm

# Build the project for deployment
# Usage: make build WEEK=3
build:
	@if [ -z "$(WEEK)" ]; then \
		echo "Please specify a week, e.g., make build WEEK=3"; \
		exit 1; \
	fi
	./build.sh build --week $(WEEK)

# Generate an LLM report for a specific week
# Usage: make llm WEEK=3
llm:
	@if [ -z "$(WEEK)" ]; then \
		echo "Please specify a week, e.g., make llm WEEK=3"; \
		exit 1; \
	fi
	python -m ff.llm_report --week $(WEEK)

# Preview a weekly report
# Usage: make preview WEEK=3
preview:
	@if [ -z "$(WEEK)" ]; then \
		echo "Please specify a week, e.g., make preview WEEK=3"; \
		exit 1; \
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
