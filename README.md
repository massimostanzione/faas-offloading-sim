## Requirements

(Optional) Prepare a virtual environment:

	python -m venv env
	source env/bin/activate
	pip install -r requirements.txt 

## Usage

	python main.py [<config file>]

## Configuration

Default configuration file is `./config.ini` (can be overridden as shown above).
Example configuration:

	[seed]
	arrival = 1
	service = 5

	[simulation]
	close-door-time = 300

	[fun_f1]
	arrival-rate = 1
	service-time-mean = 0.5
	service-time-scv = 2
	memory = 100

	[class_default]
	arrival-weight = 1
	deadline = 1.0
	utility = 1.0

	[class_premium]
	arrival-weight = 0.2
	deadline = 1.0
	utility = 2.0
