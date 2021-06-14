# quality-momentum
Sandbox for playing around with quality momentum

# Docker instructions for running bot components

`cp .env.template .env`
Edit your newly created .env file with your Quandl API Key. This file will be copied into your Dockerfile.

> DISCLAIMER: If distributing docker image, we'll need to rework secrets/config.

Explore the Makefile for all availabe build actions. Most commands are simple wrappers around docker-compose.
```sh
# Run a jupyter notebook
make run
# Navigate to http://127.0.0.1:8888

# Run test suite
make test
```

# Running tests