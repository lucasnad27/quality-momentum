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

# Pre-cache data from AWS S3 to improve backtesting performance
make cache S3_BUCKET=prod-stock-universe DATA_DIR=s3_data/

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

> NOTE: I'm unable to get the `launch.json` "Python: Remote Attach" configuration to successfully run the `docker-run: debug` as a `preLaunchTask`. I hope to resolve this issue so that upon running this debugger, an up to date container will automatically run, allowing pytest suite to be ran on the active file ππΌππΌππΌ

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

## Initial results from 30-year backtest

|Strategy                     |Compound Annual Growth Rate (CAGR)|Sharpe Ratio|
|-----------------------------------------------------------------------------|
|QM-15th Percentile Market Cap|15.521%                           |0.60        |
|QM-30th Percentile Market Cap|19.577%                           |0.69        |
|QM-40th Percentile Market Cap|19.519%                           |0.69        |
|QM-60th Percentile Market Cap|19.577%                           |0.69        |
|QM-90th Percentile Market Cap|19.577%                           |0.69        |
|S&P 500                      |9.92%                             |0.41        |
