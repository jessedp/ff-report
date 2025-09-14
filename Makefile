# Makefile for Fantasy Football App

.PHONY: build deploy dry-run

# Build the project by running the build script
build:
	./build.sh

# Deploy the built dist/ to the remote server
deploy:
	rsync -avz --quiet --delete dist/ ls2:/var/www/tbol/ff/

# Dry-run to see what would be deployed without actually doing it
dry-run:
	rsync -avz --delete --dry-run dist/ ls2:/var/www/tbol/ff/

# Clean up the dist/ directory
clean:
	rm -rf dist/

preview:
	./preview.sh $(ARGS)
