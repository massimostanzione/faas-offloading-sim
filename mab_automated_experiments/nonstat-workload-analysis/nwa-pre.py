import itertools
import json
import os
import sys
from multiprocessing import Pool
from typing import List

import conf
from main import main

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

from mab_automated_experiments._internal import consts
from mab_automated_experiments._internal.bayesopt import bayesopt_search
from mab_automated_experiments._internal.experiment import MABExperiment, write_custom_configfile
from mab_automated_experiments._internal.logging import MABExperimentInstanceRecord, IncrementalLogger, LOOKUP_OPTIMAL_PARAMETERS

with open(os.path.join(SCRIPT_DIR,"custom-arrivals.json"), 'r') as f:
    data = json.load(f)
    wl_conf_names=[]
    for d in data:
        arrivals=[]
        print(d["name"], d["f1"])
        wl_conf_names.append(d["name"])

# le tracce
wl_conf_names.append("trace-f1linear")
wl_conf_names.append("trace-f1gauss")

experiment_confpath = os.path.join(consts.EXPCONF_FILE)

expconf = conf.parse_config_file(os.path.join(SCRIPT_DIR, experiment_confpath))
strategies = expconf["strategies"]["strategies"].split(consts.DELIMITER_COMMA)
seeds = expconf["parameters"]["seeds"].split(consts.DELIMITER_COMMA)
axis_pre = expconf["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
axis_post = expconf["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
is_single_axis = axis_post == ['']

# qui gestito custom
max_procs = expconf.getint("experiment", "max-parallel-execution")

rundup = expconf["output"]["run-duplicates"]

expname = "nonstat-workload-analysis"

for wl_name in wl_conf_names:

    specfilename = os.path.join(SCRIPT_DIR, "results",
                            "spec" + wl_name + consts.SUFFIX_SPECSFILE)
    os.makedirs(os.path.join(expname, "results"), exist_ok=True)
    if not wl_name.find("trace-")!=-1:
        with open(os.path.join(SCRIPT_DIR, "custom-arrivals.json"), 'r') as f:
            data = json.load(f)
            for d in data:
                if d["name"] == wl_name:
                    for func_progr in range(1, 5 + 1, 1):
                        func = "f" + str(func_progr)
                        arrivals.append({"node": 'lb1', "function": func, 'rate': d[func]})

                    with open(specfilename, "w") as outf:
                        spec.write_spec_custom(outf, functions, classes, nodes, arrivals)
    else:
        with open(specfilename, "w") as outf:
            func="f1"
            arrivals_trace=[{"node": 'lb1', "function": func, 'trace': os.path.join(SCRIPT_DIR, wl_name+".iat")}]
            spec.write_spec_custom(outf, functions, classes, nodes, arrivals_trace)


# iterate among {strategies x axis_pre x axis_post}
all_combinations = list(itertools.product(strategies, axis_pre, seeds, wl_conf_names))

in_list=[]
for strat, axis, seed, wl_name in all_combinations:
    instance = MABExperimentInstanceRecord(strat, axis, axis, None, seed, wl_name)
    in_list.append(instance)
out_list=bayesopt_search(in_list, max_procs, expconf)

logger = IncrementalLogger()

def _parall_run(instance:MABExperimentInstanceRecord):


        exec = logger.determine_simex_behavior(instance, rundup, ["policies", "cumavg-reward"])
        if exec:
            params=instance.identifiers["parameters"]
            strat=instance.identifiers["strategy"]
            axis_pre=instance.identifiers["axis_pre"]
            axis_post=instance.identifiers["axis_pre"]
            seed=instance.identifiers["seed"]
            specfilename = os.path.join(SCRIPT_DIR, "results",
                                    "spec" + instance.identifiers["workload"] + consts.SUFFIX_SPECSFILE)
            configpath = write_custom_configfile(expname, strat, axis_pre, axis_post, list(params.keys()), list(params.values()),
                                                 seed, specfilename)
            main(configpath)

            # processa l'output
            # (ev. nel post-processing)
            mabfile = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_stats", consts.PREFIX_MABSTATSFILE+"-pid"+str(os.getpid()))+consts.SUFFIX_MABSTATSFILE)
            with open(mabfile, 'r') as f:
                data = json.load(f)
            policies = []
            rewards = []
            for d in data:
                policies.append(d["policy"])
                rewards.append(d['reward'])

            cumavg_reward = sum(rewards) / len(rewards)
            instance.add_experiment_result({"policies":policies,"cumavg-reward":cumavg_reward})
            logger.persist(instance)

with Pool(processes=max_procs) as pool:
    pool.map(_parall_run, out_list)

def compute_steadypol(list:List[str])->str:
    threshold=0.85
    policies_freqs = {"random-lb": 0, "round-robin-lb": 0, "mama-lb": 0, "const-hash-lb": 0,
                      "wrr-speedup-lb": 0,
                      "wrr-memory-lb": 0, "wrr-cost-lb": 0}
    for policy in list:
        policies_freqs[policy]+=1

    best=[]
    for k, v in policies_freqs.items():
        if v>=threshold*len(list):
            best.append(k)

    if len(best)==1: return best[0]
    if len(best)>1: return "**** più maggioritarie"
    return "N.D."


output_file_hr = (expname + "/results/output-humanreadable")
with open(output_file_hr, "a") as mp_file:
    needs_header = not os.path.exists(output_file_hr)
    if needs_header:
        mp_file.write(
            "strategy axis       workload   reward             steady-lb-policy\n")
        mp_file.write(
            "------------------------------------------------------------------------------------------------------------------------\n")

    for strat in strategies:
        for axis in axis_pre:
            for wl_name in wl_conf_names:
                for seed in seeds:
                    instance=MABExperimentInstanceRecord(strat, axis, axis, LOOKUP_OPTIMAL_PARAMETERS, seed, wl_name)
                    found=logger.lookup(instance)
                    reward=found.results["cumavg-reward"]
                    steadypol=compute_steadypol(found.results["policies"])
                    mp_file.write('{0:8} {1:10} {2:15} {3:25} {4}\n'
                    .format(
                        strat,
                        axis,
                        wl_name,
                        reward,
                        steadypol
                            ))
            mp_file.write("\n")