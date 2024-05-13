import sys
import time
import tempfile
import os
import argparse
import pandas as pd
import numpy as np

from spec import generate_temp_spec, generate_random_temp_spec
import faas
import conf
from arrivals import PoissonArrivalProcess, TraceArrivalProcess, MAPArrivalProcess
from simulation import Simulation
from infrastructure import *
from main import read_spec_file
from numpy.random import SeedSequence, default_rng

DEFAULT_CONFIG_FILE = "config.ini"
DEFAULT_OUT_DIR = "results"
DEFAULT_DURATION = 1800 # TODO
SEEDS=[1,293,287844,2902,944,9573,102903,193,456,71]
PERCENTILES=np.array([1,5,10,25,50,75,90,95,99])/100.0


def print_results (results, filename=None):
    for line in results:
        print(line)
    if filename is not None:
        with open(filename, "w") as of:
            for line in results:
                print(line,file=of)

def default_infra(edge_cloud_latency=0.100):
    # Regions
    reg_cloud = Region("cloud")
    reg_edge = Region("edge", reg_cloud)
    regions = [reg_edge, reg_cloud]
    # Latency
    latencies = {(reg_edge,reg_cloud): edge_cloud_latency, (reg_edge,reg_edge): 0.005}
    bandwidth_mbps = {(reg_edge,reg_edge): 100.0, (reg_cloud,reg_cloud): 1000.0,\
            (reg_edge,reg_cloud): 10.0}
    # Infrastructure
    return Infrastructure(regions, latencies, bandwidth_mbps)

def _experiment (config, seed_sequence, infra, spec_file_name, return_resp_times_stats=False):
    classes, functions, node2arrivals  = read_spec_file (spec_file_name, infra, config)
    #generate_latencies(infra, default_rng(seed_sequence.spawn(1)[0]))

    with tempfile.NamedTemporaryFile() as rtf:
        if return_resp_times_stats:
            config.set(conf.SEC_SIM, conf.RESP_TIMES_FILE, rtf.name)
        sim = Simulation(config, seed_sequence, infra, functions, classes, node2arrivals)
        final_stats = sim.run()
        del(sim)

        if return_resp_times_stats:
            # Retrieve response times
            df = pd.read_csv(rtf.name)
            # Compute percentiles
            rt_p = {f"RT-{k}": v for k,v in df.RT.quantile(PERCENTILES).items()}
            dat_p = {f"DAT-{k}": v for k,v in df.DataAccess.quantile(PERCENTILES).items()}

    if return_resp_times_stats:
        return final_stats, df, rt_p, dat_p
    else:
        return final_stats

def relevant_stats_dict (stats):
    result = {}
    result["Utility"] = stats.utility
    result["Penalty"] = stats.penalty
    result["NetUtility"] = stats.utility-stats.penalty
    result["Cost"] = stats.cost
    result["BudgetExcessPerc"] = max(0, (stats.cost-stats.budget)/stats.budget*100)
    return result


def experiment_main_comparison(args, config):
    results = []
    exp_tag = "mainComparison"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_POLICY, conf.SPLIT_BUDGET_AMONG_EDGE_NODES, "false")
    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")
    config.set(conf.SEC_POLICY, conf.FALLBACK_ON_LOCAL_REJECTION, "drop")
    config.set(conf.SEC_POLICY, conf.NONLINEAR_OPT_ALGORITHM, "slsqp")


    POLICIES = ["basic-budget", "probabilistic", "probabilistic-offline"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass


    for poisson_arrivals in [True, False]:
        for seed in SEEDS:
            config.set(conf.SEC_SIM, conf.SEED, str(seed))
            seed_sequence = SeedSequence(seed)
            for functions in [5]:
                for penalty_mode in ["default", "drop", "deadline", "none"]:
                    for budget in [-1, 0.1, 1]:
                        config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, str(budget))
                        for edge_enabled in [True,False]:
                            config.set(conf.SEC_POLICY, conf.EDGE_OFFLOADING_ENABLED, str(edge_enabled))
                            for edge_memory in [1024, 2048, 4096]:
                                for pol in POLICIES:
                                    config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)
                                    if "probabilistic" in pol:
                                        optimizers = ["nonlinear", "nonlinear-lp-relaxed", "iterated-lp"]
                                    else:
                                        optimizers = ["-"]
                                    for opt in optimizers:
                                        config.set(conf.SEC_POLICY, conf.QOS_OPTIMIZER, opt)

                                        if "probabilistic" in pol and "lp-relaxed" in opt:
                                            config.set(conf.SEC_POLICY, conf.ADAPTIVE_LOCAL_MEMORY, str(True))
                                        else:
                                            config.set(conf.SEC_POLICY, conf.ADAPTIVE_LOCAL_MEMORY, str(False))

                                        if "probabilistic" in pol and opt == "nonlinear":
                                            approximation_vals = [None, "linear", "poly2", "poly", "poly2-allx"]
                                        else:
                                            approximation_vals = [None]

                                        for blockin_approx in approximation_vals:
                                            config.set(conf.SEC_POLICY, conf.NONLINEAR_APPROXIMATE_BLOCKING, str(blockin_approx))

                                            keys = {}
                                            keys["Policy"] = pol
                                            keys["Seed"] = seed
                                            keys["Optimizer"] = opt
                                            keys["Budget"] = budget
                                            keys["Functions"] = functions
                                            keys["EdgeMemory"] = edge_memory
                                            keys["EdgeEnabled"] = edge_enabled
                                            keys["PenaltyMode"] = penalty_mode
                                            keys["PoissonArrivals"] = poisson_arrivals
                                            keys["BlockingApprox"] = blockin_approx

                                            run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                                            # Check if we can skip this run
                                            if old_results is not None and not\
                                                    old_results[(old_results.Seed == seed) &\
                                                        (old_results.Optimizer == opt) &\
                                                        (old_results.PenaltyMode == penalty_mode) &\
                                                        (old_results.EdgeEnabled == edge_enabled) &\
                                                        (old_results.Functions == functions) &\
                                                        (old_results.Budget == budget) &\
                                                        (old_results.BlockingApprox == blockin_approx) &\
                                                        (old_results.PoissonArrivals == poisson_arrivals) &\
                                                        (old_results.EdgeMemory == edge_memory) &\
                                                        (old_results.Policy == pol)].empty:
                                                print("Skipping conf")
                                                continue

                                            rng = default_rng(seed_sequence.spawn(1)[0])
                                            temp_spec_file = generate_random_temp_spec (rng, n_functions=functions, edge_memory=edge_memory, force_poisson_arrivals=poisson_arrivals)
                                            infra = default_infra(edge_cloud_latency=0.1)
                                            stats = _experiment(config, seed_sequence, infra, temp_spec_file.name)
                                            temp_spec_file.close()
                                            with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_{run_string}.json"), "w") as of:
                                                stats.print(of)

                                            result=dict(list(keys.items()) + list(relevant_stats_dict(stats).items()))
                                            results.append(result)
                                            print(result)

                                            resultsDf = pd.DataFrame(results)
                                            if old_results is not None:
                                                resultsDf = pd.concat([old_results, resultsDf])
                                            resultsDf.to_csv(outfile, index=False)
    
    resultsDf = pd.DataFrame(results)
    if old_results is not None:
        resultsDf = pd.concat([old_results, resultsDf])
    resultsDf.to_csv(outfile, index=False)
    print(resultsDf.groupby(["Policy", "Optimizer"]).mean(numeric_only=True))

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)


def experiment_optimizers(args, config):
    results = []
    exp_tag = "optimizers"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_POLICY, conf.SPLIT_BUDGET_AMONG_EDGE_NODES, "false")
    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")
    config.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, str(1))
    config.set(conf.SEC_POLICY, conf.POLICY_NAME, "probabilistic-offline")


    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        seed_sequence = SeedSequence(seed)
        for edge_enabled in [True,False]:
            config.set(conf.SEC_POLICY, conf.EDGE_OFFLOADING_ENABLED, str(edge_enabled))
            for latency in [0.100]:
                for functions in [2,3,5]:
                    for budget in [-1, 0.1, 1]:
                        config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, str(budget))
                        for opt in ["nonlinear", "nonlinear-noguess", "nonlinear-lp-relaxed", "nonlinear-lp-relaxed-threshold", "iterated-lp"]:
                            config.set(conf.SEC_POLICY, conf.QOS_OPTIMIZER, opt)

                            if "relaxed" in opt:
                                algs = ["-"]
                                use_lp_for_bounds_vals = [False]
                                max_p_block_vals = [0.0]
                                approximation_vals = ["none"]
                            elif "iterated" in opt:
                                algs = ["-"]
                                use_lp_for_bounds_vals = [False]
                                max_p_block_vals = [0.01, 0.05, 0.1, 0.2]
                                approximation_vals = ["none"]
                            else:
                                #algs = ["trust-region", "slsqp"] # TODO
                                algs = ["slsqp"]
                                use_lp_for_bounds_vals = [True, False]
                                max_p_block_vals = [0.0]
                                approximation_vals = ["none", "linear", "poly", "poly2", "poly2-allx", "poly5"]

                            for alg in algs:
                                config.set(conf.SEC_POLICY, conf.NONLINEAR_OPT_ALGORITHM, alg)
                                for use_lp_for_bounds in use_lp_for_bounds_vals:
                                    config.set(conf.SEC_POLICY, conf.NONLINEAR_USE_LP_FOR_BOUNDS, str(use_lp_for_bounds))
                                    for max_p_block in max_p_block_vals:
                                        config.set(conf.SEC_POLICY, conf.ITERATED_LP_MAX_PBLOCK, str(max_p_block))
                                        for blockin_approx in approximation_vals:
                                            config.set(conf.SEC_POLICY, conf.NONLINEAR_APPROXIMATE_BLOCKING, str(blockin_approx))

                                            keys = {}
                                            keys["Optimizer"] = opt
                                            keys["Alg"] = alg
                                            keys["Seed"] = seed
                                            keys["Latency"] = latency
                                            keys["MaxPBlock"] = max_p_block
                                            keys["EdgeEnabled"] = edge_enabled
                                            keys["Functions"] = functions
                                            keys["BlockingApprox"] = blockin_approx
                                            keys["Budget"] = budget
                                            keys["UseLPForBounds"] = use_lp_for_bounds

                                            run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                                            # Check if we can skip this run
                                            if old_results is not None and not\
                                                    old_results[(old_results.Seed == seed) &\
                                                        (old_results.Latency == latency) &\
                                                        (old_results.Budget == budget) &\
                                                        (old_results.Functions == functions) &\
                                                        (old_results.Alg == alg) &\
                                                        (old_results.MaxPBlock == max_p_block) &\
                                                        (old_results.BlockingApprox == blockin_approx) &\
                                                        (old_results.EdgeEnabled == edge_enabled) &\
                                                        (old_results.UseLPForBounds == use_lp_for_bounds) &\
                                                        (old_results.Optimizer == opt)].empty:
                                                print("Skipping conf")
                                                continue

                                            rng = default_rng(seed_sequence.spawn(1)[0])
                                            temp_spec_file = generate_random_temp_spec (rng, n_functions=functions)
                                            infra = default_infra(edge_cloud_latency=latency)

                                            t0 = time.time()
                                            stats = _experiment(config, seed_sequence, infra, temp_spec_file.name)
                                            temp_spec_file.close()
                                            t1 = time.time()

                                            with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_{run_string}.json"), "w") as of:
                                                stats.print(of)

                                            result=dict(list(keys.items()))# + list(relevant_stats_dict(stats).items()))

                                            # NOTE: we assume that only 1 node solves the problem
                                            result["Obj"] = max(stats.optimizer_obj_value.values())
                                            result["ExecTime"] = t1-t0
                                            results.append(result)
                                            print(result)

                                            resultsDf = pd.DataFrame(results)
                                            if old_results is not None:
                                                resultsDf = pd.concat([old_results, resultsDf])
                                            resultsDf.to_csv(outfile, index=False)
    
    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

def experiment_scalability (args, config):
    results = []
    exp_tag = "scalability"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, str("400"))
    config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "naive-per-function")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "no")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")
    config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, "10")


    POLICIES = ["probabilistic-legacy", "probabilistic"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        for n_classes in [1, 2, 4, 6, 8]:
            for functions in range(2,161,4):
                for pol in POLICIES:
                    config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

                    keys = {}
                    keys["Policy"] = pol
                    keys["Seed"] = seed
                    keys["Functions"] = functions
                    keys["Classes"] = n_classes

                    run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                    # Check if we can skip this run
                    if old_results is not None and not\
                            old_results[(old_results.Seed == seed) &\
                                (old_results.Classes == n_classes) &\
                                (old_results.Functions == functions) &\
                                (old_results.Policy == pol)].empty:
                        print("Skipping conf")
                        continue

                    temp_spec_file = generate_temp_spec (n_functions=functions, n_classes=n_classes)
                    infra = default_infra()
                    stats = _experiment(config, infra, temp_spec_file.name)
                    temp_spec_file.close()
                    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_{run_string}.json"), "w") as of:
                        stats.print(of)
                    
                    
                    
                    result=dict(list(keys.items()) + list(relevant_stats_dict(stats).items()))

                    update_time = max([
                        stats._policy_update_time_sum[n]/stats._policy_updates[n] for n in infra.get_nodes()
                        ])
                    result["updateTime"] = update_time

                    results.append(result)
                    print(result)

                    resultsDf = pd.DataFrame(results)
                    if old_results is not None:
                        resultsDf = pd.concat([old_results, resultsDf])
                    resultsDf.to_csv(outfile, index=False)
    
    resultsDf = pd.DataFrame(results)
    if old_results is not None:
        resultsDf = pd.concat([old_results, resultsDf])
    resultsDf.to_csv(outfile, index=False)
    print(resultsDf.groupby("Policy").mean())

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', action='store', required=False, default="", type=str)
    parser.add_argument('--force', action='store_true', required=False, default=False)
    parser.add_argument('--debug', action='store_true', required=False, default=False)
    parser.add_argument('--seed', action='store', required=False, default=None, type=int)

    args = parser.parse_args()

    config = conf.parse_config_file("default.ini")
    config.set(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, "-1")
    config.set(conf.SEC_SIM, conf.PRINT_FINAL_STATS, "false")
    config.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, str(DEFAULT_DURATION))

    if args.debug:
        args.force = True
        SEEDS=SEEDS[:1]

    if args.seed is not None:
        SEEDS = [int(args.seed)]
    
    if args.experiment.lower() == "a":
        experiment_main_comparison(args, config)
    elif args.experiment.lower() == "o":
        experiment_optimizers(args, config)
    elif args.experiment.lower() == "s":
        experiment_scalability(args, config)
    else:
        print("Unknown experiment!")
        exit(1)
