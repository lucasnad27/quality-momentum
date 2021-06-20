setup:
	export DOCKER_BUILDKIT=1

run:

run: setup
	docker-compose up -d --build jupyter

stop:
	docker-compose stop jupyter

build: setup
	docker build --target=primary . -t qualitymomentum:primary

test: build
	docker run qualitymomentum:primary pytest ./tests

pip_compile:
	pip-compile ./setup/requirements.in && pip-compile ./setup/testing-requirements.in && pip-compile ./setup/local-requirements.in

pip_sync:
	pip-sync setup/requirements.txt setup/local-requirements.txt setup/testing-requirements.txt
