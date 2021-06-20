run: stop up

setup:
	export DOCKER_BUILDKIT=1

up: setup
	docker-compose -f docker-compose.yml up -d --build

stop:
	docker-compose -f docker-compose.yml stop

down:
	docker-compose -f docker-compose.yml down

test: setup
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down --volumes

shell: setup
	docker-compose run --rm test
