import itertools
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import conf

classes = [{'name': 'standard', 'max_resp_time': 0.5, 'utility': 0.01, 'arrival_weight': 0.7},
           {'name': 'critical_1', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 0.1},
           {'name': 'critical_2', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 0.1, 'deadline_penalty': 0.75,
            'drop_penalty': 0.75},
           {'name': 'batch', 'max_resp_time': 100.0, 'utility': 1.0, 'arrival_weight': 0.1}
           ]
nodes = [
    {'name': 'cloud1', 'region': 'cloud', 'cost': 0.000005, 'policy': 'cloud', 'speedup': 0.5, 'memory': 8000},
    {'name': 'cloud2', 'region': 'cloud', 'cost': 0.000005, 'policy': 'cloud', 'speedup': 0.5, 'memory': 8000},
    {'name': 'cloud3', 'region': 'cloud', 'cost': 0.00001, 'policy': 'cloud', 'speedup': 1.0, 'memory': 16000},
    {'name': 'cloud4', 'region': 'cloud', 'cost': 0.00001, 'policy': 'cloud', 'speedup': 1.0, 'memory': 16000},
    {'name': 'cloud5', 'region': 'cloud', 'cost': 0.00003, 'policy': 'cloud', 'speedup': 1.2, 'memory': 16000},
    {'name': 'cloud6', 'region': 'cloud', 'cost': 0.00005, 'policy': 'cloud', 'speedup': 1.2, 'memory': 24000},
    {'name': 'cloud7', 'region': 'cloud', 'cost': 0.00007, 'policy': 'cloud', 'speedup': 1.4, 'memory': 24000},
    {'name': 'cloud8', 'region': 'cloud', 'cost': 0.0001, 'policy': 'cloud', 'speedup': 1.4, 'memory': 32000},
    {'name': 'lb1', 'region': 'cloud', 'policy': 'random-lb', 'memory': 0}

]

functions = [{'name': 'f1', 'memory': 512, 'duration_mean': 0.4, 'duration_scv': 1.0, 'init_mean': 0.5},
             {'name': 'f2', 'memory': 512, 'duration_mean': 0.2, 'duration_scv': 1.0, 'init_mean': 0.25},
             {'name': 'f3', 'memory': 128, 'duration_mean': 0.3, 'duration_scv': 1.0, 'init_mean': 0.6},
             {'name': 'f4', 'memory': 1024, 'duration_mean': 0.25, 'duration_scv': 1.0, 'init_mean': 0.25},
             {'name': 'f5', 'memory': 256, 'duration_mean': 0.45, 'duration_scv': 1.0, 'init_mean': 0.5}]
"""
arrivals_enrico = [
    {"node": 'lb1', 'function': 'f1', 'rate': 1},
    {"node": 'lb1', 'function': 'f2', 'rate': 10},
    {"node": 'lb1', 'function': 'f3', 'rate': 15},
    {"node": 'lb1', 'function': 'f4', 'rate': 1},
    {"node": 'lb1', 'function': 'f5', 'rate': 3},
]

arrivals_f1 = [
    {"node": 'lb1', 'function': 'f1', 'rate': 1},
    {"node": 'lb1', 'function': 'f2', 'rate': 10},
    {"node": 'lb1', 'function': 'f3', 'rate': 15},
    {"node": 'lb1', 'function': 'f4', 'rate': 1},
    {"node": 'lb1', 'function': 'f5', 'rate': 3},
]

arrivals_f2 = [
    {"node": 'lb1', 'function': 'f1', 'rate': 50},
    {"node": 'lb1', 'function': 'f2', 'rate': 5},
    {"node": 'lb1', 'function': 'f3', 'rate': 5},
    {"node": 'lb1', 'function': 'f4', 'rate': 5},
    {"node": 'lb1', 'function': 'f5', 'rate': 5},
]

arrivals_f3 = [
    {"node": 'lb1', 'function': 'f1', 'rate': 5},
    {"node": 'lb1', 'function': 'f2', 'rate': 50},
    {"node": 'lb1', 'function': 'f3', 'rate': 5},
    {"node": 'lb1', 'function': 'f4', 'rate': 5},
    {"node": 'lb1', 'function': 'f5', 'rate': 5},
]

arrivals_f4 = [
    {"node": 'lb1', 'function': 'f1', 'rate': 5},
    {"node": 'lb1', 'function': 'f2', 'rate': 5},
    {"node": 'lb1', 'function': 'f3', 'rate': 50},
    {"node": 'lb1', 'function': 'f4', 'rate': 5},
    {"node": 'lb1', 'function': 'f5', 'rate': 5},
]

arrivals_f5 = [
    {"node": 'lb1', 'function': 'f1', 'rate': 5},
    {"node": 'lb1', 'function': 'f2', 'rate': 5},
    {"node": 'lb1', 'function': 'f3', 'rate': 5},
    {"node": 'lb1', 'function': 'f4', 'rate': 5},
    {"node": 'lb1', 'function': 'f5', 'rate': 50},
]

"""

import spec

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _internal import consts
from _internal.bayesopt import bayesopt_search

print(SCRIPT_DIR)
with open(os.path.join(SCRIPT_DIR,"custom-arrivals.json"), 'r') as f:
    data = json.load(f)
    wl_conf_names=[]
    for d in data:
        arrivals=[]
        print(d["name"], d["f1"])
        wl_conf_names.append(d["name"])

experiment_confpath = os.path.join(consts.EXPCONF_FILE)

# TODO anche altrove, nell'apertura del configfile, non serve la open
#with open(os.path.join(SCRIPT_DIR,experiment_confpath), "r") as expconf_file:

config = conf.parse_config_file(os.path.join(SCRIPT_DIR,experiment_confpath))
strategies = config["strategies"]["strategies"].split(consts.DELIMITER_COMMA)
seeds = config["parameters"]["seeds"].split(consts.DELIMITER_COMMA)
axis_pre = config["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
axis_post = config["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
is_single_axis = axis_post == ['']

# qui gestito custom
max_procs = config.getint("experiment", "max-parallel-execution")

rundup = config["output"]["run-duplicates"]

# iterate among {strategies x axis_pre x axis_post}
all_combinations = list(itertools.product(strategies, axis_pre, seeds, wl_conf_names)) # FIXME if is_single_axis else itertools.product(strategies, axis_pre, axis_post, seeds, wl_conf_names)
chunk_size = len(all_combinations) // max_procs + (len(all_combinations) % max_procs > 0)
chunks = [all_combinations[i:i + chunk_size] for i in range(0, len(all_combinations), chunk_size)]



def _parall_run(params):
    expname="nonstat-workload-analysis"
    for strat, axis, seed, wl_name in params:

        # genera specfile
        # TODO vedere se si può generalizzare in qualche modo anziché lasciarlo custom come è ora
        specfilename=os.path.join(SCRIPT_DIR,"results", "spec.yml-pid"+str(os.getpid()))
        with open(os.path.join(SCRIPT_DIR,"custom-arrivals.json"), 'r') as f:
            data = json.load(f)
            for d in data:
                if d["name"]==wl_name:
                    for func_progr in range(1, 5 + 1, 1):
                        func = "f" + str(func_progr)
                        arrivals.append({"node": 'lb1', "function": func, 'rate': d[func]})
                        os.makedirs(os.path.join(expname,"results"), exist_ok=True)

                    with open(specfilename, "w") as outf:
                        spec.write_spec_custom(outf, functions, classes, nodes, arrivals)
                        # TODO poi rimuoverli
        # vai di ricerca bayesiana
        #print(config)
        params=bayesopt_search(expname, strat, axis,specfilename,seed,config, rundup, wl_name)

        # crea esperimento con suddetto specfile e parametri ottimi

        # eseguilo

        # processa l'output
        # (ev. nel post-processing)




with Pool(processes=max_procs) as pool:
    pool.map(_parall_run, chunks)