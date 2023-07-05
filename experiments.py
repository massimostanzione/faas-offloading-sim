import sys
import re
import argparse
import numpy as np
import pandas as pd

import faas
import conf
from arrivals import PoissonArrivalProcess, TraceArrivalProcess
from simulation import Simulation
from infrastructure import *
from main import read_spec_file

DEFAULT_CONFIG_FILE = "config.ini"


def print_results (results, filename=None):
    for line in results:
        print(line)
    if filename is not None:
        with open(filename, "w") as of:
            for line in results:
                print(line,file=of)

def default_infra():
    # Regions
    reg_cloud = Region("cloud")
    reg_edge = Region("edge", reg_cloud)
    regions = [reg_edge, reg_cloud]
    # Latency
    latencies = {(reg_edge,reg_cloud): 0.100}
    bandwidth_mbps = {(reg_edge,reg_edge): 100.0, (reg_cloud,reg_cloud): 1000.0,\
            (reg_edge,reg_cloud): 10.0}
    # Infrastructure
    return Infrastructure(regions, latencies, bandwidth_mbps)

def _experiment (config):
    infra = default_infra()
    spec_file_name = config.get(conf.SEC_SIM, conf.SPEC_FILE, fallback=None)
    classes, functions, node2arrivals  = read_spec_file (spec_file_name, infra)
    sim = Simulation(config, infra, functions, classes, node2arrivals)
    final_stats = sim.run()
    return final_stats


def experiment_main_comparison(args, debug=False):
    config = conf.parse_config_file(DEFAULT_CONFIG_FILE)
    config.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, "2")

    results = []
    outfile="resultsMainComparison.csv"

    #SEEDS=[1,293,287844,2902,944,9573,102903,193,456,71]
    SEEDS=[1]
    POLICIES = ["probabilistic", "probabilistic2", "greedy"]

    # Check existing results
    try:
        old_results = pd.read_csv(outfile)
    except:
        old_results = None

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))

        for pol in POLICIES:
            config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

            # Check if we can skip this run
            if old_results is not None:
                if not old_results[(old_results.Seed == seed) &\
                        (old_results.Policy == pol)].empty:
                    print("Skipping conf")
                    continue


            stats = _experiment(config)

            result = {}
            result["Policy"] = pol
            result["Seed"] = seed
            result["Utility"] = stats.utility

            results.append(result)
            print(result)
    
    resultsDf = pd.DataFrame(results)
    if old_results is not None:
        resultsDf = pd.concat([old_results, resultsDf])
    resultsDf.to_csv(outfile, index=False)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', action='store', required=False, default="", type=str)

    args = parser.parse_args()
    
    if args.experiment.lower() == "a":
        experiment_main_comparison(args)
    else:
        print("Unknown experiment!")
        exit(1)
