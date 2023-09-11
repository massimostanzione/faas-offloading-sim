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

An example `spec.yml` file is provided as `spec.yml.example` in this repository.


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

## Stateful

Each node stores key-value pairs. The `kv_store` field of the FaaS Node
associates each key with the size (in bytes) of the corresponding value.

The `KeyLocator` class and the `key_locator` object defined in `stateful.py` 
provide each node the ability to discover which node stores a certain key.

You can specify the list of keys accessed by a function in the spec file.
Each key can be associated with a probability (default 1.0) of being accessed at each
function invocation and the size of the corresponding value (default 100 bytes).
Example:

```
functions:
  - name: f1
    memory: 1024
    duration_mean: 0.240
    duration_scv: 1.0
    keys:
      - key: a
        probability: 0.3
      - key: b
        size: 400
```
