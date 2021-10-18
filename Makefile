setup:
	export DOCKER_BUILDKIT=1

run: setup
	docker-compose up -d --build jupyter

cache:
	aws s3 sync s3://$(S3_BUCKET)/ ./$(DATA_DIR)

stop:
	docker-compose stop jupyter

build: setup
	docker build --target=primary . -t qualitymomentum:primary

test: build
	docker run qualitymomentum:primary pytest ./tests

pip_compile:
	pip-compile ./setup/requirements.in

pip_sync:
	pip-sync setup/requirements.txt
