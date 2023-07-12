This software simulates the execution of a FaaS system deployed over Edge and 
Cloud nodes.


## Requirements

The simulator is written in Python.
You can run it within a virtual environment installing the dependencies listed
in `requirements.txt`. E.g.:

	python -m venv env
	source env/bin/activate
	pip install -r requirements.txt 

You may also need to install the GLPK solver.

## Usage

The simulator is started as follows:

	python main.py [<config file>]

If no configuration file is specified, `./config.ini` is used.

## Configuration

Two key files are responsible for the configuration: 

- the main `.ini` configuration file
- a YAML specification file of available QoS classes, functions, nodes and
workload

Note that the main configuration file contains a reference to the 
associated specification file (`spec-file` option, as shown below).

Example `.ini` configuration:

    [simulation]
    stats-print-interval = 1200
    stats-print-file = stats.txt
    close-door-time = 1000
    plot-rt = false
    seed = 123
    spec-file = spec.yml

    [policy]
    name = basic
    update-interval = 120
    arrival-alpha = 0.3

    [container]
    init-time = 1.1

Example `spec.yml`:

    classes:
    - name: critical
        max_resp_time: 0.500
        utility: 1.0 
        arrival_weight: 1.0
    - name: best-effort
        max_resp_time: 0.500
        utility: 0.1 
        arrival_weight: 1.0
    - name: deferrable
        max_resp_time: 5.0
        utility: 0.5 
        arrival_weight: 1.0
    nodes:
    - name: edge1
        region: edge
        memory: 2048
    - name: edge2
        region: edge
        memory: 2048
        policy: basic
    - name: edge3
        region: edge
        memory: 2048
    - name: cloud1
        region: cloud
        cost: 0.00001
        speedup: 1.1
        memory: 32000
    functions:
    - name: f1
        memory: 1024
        duration_mean: 0.240
        duration_scv: 1.0
    - name: f2
        memory: 512
        duration_mean: 0.120
        duration_scv: 1.0
    arrivals:
    - node: edge1
        function: f1
        classes:
        - best-effort
        rate: 0.1
    - node: edge2
        function: f2
        trace: traces/iat_660323aa6f1012c8eca3c7d8153cb436320b48ed84f82bf3e816b494ad8dfde2


### Arrival traces

Each function is associated with an arrival process. Incoming requests
are randomly associated with a QoS class based on the `arrival-weight` attribute
of each class (i.e., the higher the weight, the higher the probability of
belonging to the class). 

You can either specify:

- a constant average `rate` for the function: arrivals will follow a
Poisson process.
- an inter-arrival times (IATs) trace file, using the `trace` attribute. The
  trace is a text file containing IATs, one per line.

### Policies

The following policies are currently implemented:

- `basic`: heuristic policy that schedules all the requests for
  local execution when possible
- `greedy`: greedy heuristic that schedules requests so as to minimize the expected response time
- `probabilistic`: probabilistic heuristic, whose probabilities are periodically
  updated solving a LP problem
- `random`

### Configuring the *Probabilistic* policy

You may want to adjust the following parameters when using the 
`probabilistic` policy:

- `update-interval`: how often (in seconds) the probabilities should be 
updated via optimization
- `arrival-alpha`: the arrival rate of each function-class pair is tracked using
an Exponential Moving Average, whose 0 < `alpha` <= 1 parameter is set by this
configuration option (e.g., a value closer to 1.0 means we weigh recent
observations as more important).

## Utilities

Specific scripts can be used to run single experiments, e.g.:

	python experiment_policies.py

**Work in progress**: to process the JSON produced in `stats.txt` by a single
run:

	python utils/process_stats_json.py
