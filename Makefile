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
