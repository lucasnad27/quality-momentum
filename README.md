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

# Kill jupyter server
make stop

# Run test suite
make test
```

# Editor Support

> NOTE: Only VSCode has optimized workflows for common tasks such as breakpoint support within the docker container, running individual tests, etc., Many of these workflows can be optimized in other IDEs.

## VSCode

Below you can find a sample `tasks.json` and `launch.json` file that provides some handy utilities for local development. The `docker-run: debug` task will
1. build an image that runs a debugpy server
2. run a container based on that image that runs pytest

From here you can run the `Python: Remotee Attach" debugger and hit breakpoints within your testing suite.

> NOTE: I'm unable to get the `launch.json` "Python: Remote Attach" configuration to successfully run the `docker-run: debug` as a `preLaunchTask`. I hope to resolve this issue so that upon running this debugger, an up to date container will automatically run, allowing pytest suite to be ran on the active file 🙏🏼🙏🏼🙏🏼

**tasks.json**
```json
{
	"version": "2.0.0",
	"tasks": [
		{
			"type": "docker-build",
			"label": "docker-build: debug",
			"dockerBuild": {
				"tag": "qualitymomentum:debugger",
				"dockerfile": "${workspaceFolder}/Dockerfile",
				"context": "${workspaceFolder}",
				"target": "debugger"
			}
		},
		{
			"type": "docker-run",
			"label": "docker-run: debug",
			"dependsOn":["docker-build: debug"],
			"dockerRun": {
				"image": "qualitymomentum:debugger",
				"command": "pytest ./tests",
				"ports": [
					{
						"containerPort": 5678,
						"hostPort": 5678
					}
				],
			}
		}
	]
}
```
**launch.json**
```json
{
	"version": "0.2.0",
	"configurations": [
		{
			"name": "Python: Remote Attach",
			"type": "python",
			"request": "attach",
			"connect": {
				"host": "localhost",
				"port": 5678
			},
			"pathMappings": [
				{
					"localRoot": "${workspaceFolder}",
					"remoteRoot": "."
				}
			]
		}
	]
}
```
