import sys
import yaml
import os
import argparse
import pandas as pd
import tempfile

import faas
import conf
from arrivals import PoissonArrivalProcess, TraceArrivalProcess
from simulation import Simulation
from infrastructure import *
from main import read_spec_file

DEFAULT_CONFIG_FILE = "config.ini"
DEFAULT_OUT_DIR = "results"
DEFAULT_DURATION = 3600
SEEDS=[1,293,287844,2902,944,9573,102903,193,456,71]


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

def _experiment (config, infra, spec_file_name):
    classes, functions, node2arrivals  = read_spec_file (spec_file_name, infra, config)
    sim = Simulation(config, infra, functions, classes, node2arrivals)
    final_stats = sim.run()
    del(sim)
    return final_stats

def relevant_stats_dict (stats):
    result = {}
    result["Utility"] = stats.utility
    result["Penalty"] = stats.penalty
    result["NetUtility"] = stats.utility-stats.penalty
    result["Cost"] = stats.cost
    result["BudgetExcessPerc"] = max(0, (stats.cost-stats.budget)/stats.budget*100)
    return result

def generate_spec (n_functions=5, load_coeff=1.0, dynamic_rate_coeff=1.0, arrivals_to_single_node=True,
                   n_classes=4, cloud_cost=0.00005, cloud_speedup=1.0, n_edges=5):
    ntemp = tempfile.NamedTemporaryFile(mode="w")
    classes = [{'name': 'critical', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 1.0}, {'name': 'standard', 'max_resp_time': 0.5, 'utility': 0.01, 'arrival_weight': 7.0}, {'name': 'batch', 'max_resp_time': 99.0, 'utility': 1.0, 'arrival_weight': 1.0}, {'name': 'criticalP', 'max_resp_time': 0.5, 'utility': 1.0, 'penalty': 0.75, 'arrival_weight': 1.0}]
    nodes = [{'name': 'edge1', 'region': 'edge', 'memory': 4096}, {'name': 'edge2', 'region': 'edge', 'memory': 4096}, {'name': 'edge3', 'region': 'edge', 'memory': 4096}, {'name': 'edge4', 'region': 'edge', 'memory': 4096}, {'name': 'edge5', 'region': 'edge', 'memory': 4096}, {'name': 'cloud1', 'region': 'cloud', 'cost': cloud_cost, 'speedup': cloud_speedup, 'memory': 128000}]
    functions = [{'name': 'f1', 'memory': 512, 'duration_mean': 0.4, 'duration_scv': 1.0, 'init_mean': 0.5}, {'name': 'f2', 'memory': 512, 'duration_mean': 0.2, 'duration_scv': 1.0, 'init_mean': 0.25}, {'name': 'f3', 'memory': 128, 'duration_mean': 0.3, 'duration_scv': 1.0, 'init_mean': 0.6}, {'name': 'f4', 'memory': 1024, 'duration_mean': 0.25, 'duration_scv': 1.0, 'init_mean': 0.25}, {'name': 'f5', 'memory': 256, 'duration_mean': 0.45, 'duration_scv': 1.0, 'init_mean': 0.5}]
   
    #Extend functions list if needed
    if n_functions > len(functions):
        i=0
        while n_functions > len(functions):
            new_f = functions[i].copy()
            new_f["name"] = f"f{len(functions)+1}"
            functions.append(new_f)
            i+=1
    else:
        functions = functions[:n_functions]
    function_names = [f["name"] for f in functions]

    #Extend node list if needed
    if n_edges > len(nodes) - 1:
        i=0
        while n_edges > len(nodes) - 1:
            new_f = nodes[0].copy()
            new_f["name"] = f"ne{i}"
            nodes.append(new_f)
            i+=1
    elif n_edges < len(nodes) - 1:
        new_nodes = nodes[:n_edges]
        new_nodes.append(nodes[-1])
        nodes = new_nodes

    #Extend class list if needed
    if n_classes > len(classes):
        i=0
        while n_classes > len(classes):
            new_f = classes[i].copy()
            new_f["name"] = f"c{len(classes)+1}"
            classes.append(new_f)
            i+=1
    else:
        classes = classes[:n_classes]

    total_fun_weight = sum([f["duration_mean"]*f["memory"] for f in functions])

    arrivals = []
    if arrivals_to_single_node:
        total_load = 8000*load_coeff
        for f in functions:
            rate = total_load/n_functions/(f["duration_mean"]*f["memory"])
            arrivals.append({"node": "edge1",
                            "function": f["name"],
                            "rate": rate,
                            "dynamic_coeff": dynamic_rate_coeff
                            })
    else:
        edge_nodes = [n for n in nodes if "edge" in n["name"]]
        total_load = 16000*load_coeff
        load_per_node = total_load/len(edge_nodes)
        for n in edge_nodes:
            if "cloud" in n:
                continue
            for f in functions:
                rate = load_per_node/n_functions/(f["duration_mean"]*f["memory"])
                arrivals.append({"node": n["name"],
                                "function": f["name"],
                                "rate": rate,
                                 "dynamic_coeff": dynamic_rate_coeff})

    spec = {'classes': classes, 'nodes': nodes, 'functions': functions, 'arrivals': arrivals}
    ntemp.write(yaml.dump(spec))
    ntemp.flush()
    return ntemp

def experiment_cold_start2(args, config):
    results = []
    exp_tag = "coldStartDynRate"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    temp_spec_file = generate_spec (3, load_coeff=0.1, dynamic_rate_coeff=3.0, cloud_cost=0.000001)
    config.set(conf.SEC_SIM, conf.RATE_UPDATE_INTERVAL, str(300))

    POLICIES = ["probabilistic2", "greedy", "greedy-budget"]
    CS_STRATEGIES = ["pacs", "no", "naive", "naive-per-function", "full-knowledge"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))

        for pol in POLICIES:
            config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

            for local_cs in CS_STRATEGIES:
                if local_cs == "full-knowledge" and not "greedy" in pol:
                    continue
                config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, local_cs)

                for cloud_cs in CS_STRATEGIES:
                    if cloud_cs == "full-knowledge" and not "greedy" in pol:
                        continue
                    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, cloud_cs)

                    for edge_cs in CS_STRATEGIES:
                        if "greedy" in pol and edge_cs != CS_STRATEGIES[0]:
                            continue
                        if edge_cs == "full-knowledge" and not "greedy" in pol:
                            continue
                        config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, edge_cs)

                        keys = {}
                        keys["Policy"] = pol
                        keys["Seed"] = seed
                        keys["LocalCS"] = local_cs
                        keys["CloudCS"] = cloud_cs
                        keys["EdgeCS"] = edge_cs

                        run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                        # Check if we can skip this run
                        if old_results is not None and not\
                                old_results[(old_results.Seed == seed) &\
                                    (old_results.LocalCS == local_cs) &\
                                    (old_results.CloudCS == cloud_cs) &\
                                    (old_results.EdgeCS == edge_cs) &\
                                    (old_results.Policy == pol)].empty:
                            print("Skipping conf")
                            continue

                        infra = default_infra()
                        stats = _experiment(config, infra, temp_spec_file.name)
                        with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_{run_string}.json"), "w") as of:
                            stats.print(of)

                        result=dict(list(keys.items()) + list(relevant_stats_dict(stats).items()))
                        results.append(result)

                resultsDf = pd.DataFrame(results)
                if old_results is not None:
                    resultsDf = pd.concat([old_results, resultsDf])
                resultsDf.to_csv(outfile, index=False)
    
    resultsDf = pd.DataFrame(results)
    if old_results is not None:
        resultsDf = pd.concat([old_results, resultsDf])
    resultsDf.to_csv(outfile, index=False)
    print(resultsDf.groupby(["Policy", "LocalCS", "CloudCS", "EdgeCS"]).mean())

    temp_spec_file.close()

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

# TODO: for reproducibility, cloud_cost=1e-6
def experiment_cold_start(args, config):
    results = []
    exp_tag = "coldStart"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    temp_spec_file = generate_spec (3, load_coeff=1.0, dynamic_rate_coeff=1.0)

    POLICIES = ["probabilistic2", "greedy", "greedy-budget"]
    CS_STRATEGIES = ["pacs", "no", "naive", "naive-per-function", "full-knowledge"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))

        for pol in POLICIES:
            config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

            for local_cs in CS_STRATEGIES:
                if local_cs == "full-knowledge" and not "greedy" in pol:
                    continue
                config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, local_cs)

                for cloud_cs in CS_STRATEGIES:
                    if cloud_cs == "full-knowledge" and not "greedy" in pol:
                        continue
                    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, cloud_cs)

                    for edge_cs in CS_STRATEGIES:
                        if "greedy" in pol and edge_cs != CS_STRATEGIES[0]:
                            continue
                        if edge_cs == "full-knowledge" and not "greedy" in pol:
                            continue
                        config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, edge_cs)

                        keys = {}
                        keys["Policy"] = pol
                        keys["Seed"] = seed
                        keys["LocalCS"] = local_cs
                        keys["CloudCS"] = cloud_cs
                        keys["EdgeCS"] = edge_cs

                        run_string = "_".join([f"{k}{v}" for k,v in keys.items()])
                        print(f"Running: {run_string}")

                        # Check if we can skip this run
                        if old_results is not None and not\
                                old_results[(old_results.Seed == seed) &\
                                    (old_results.LocalCS == local_cs) &\
                                    (old_results.CloudCS == cloud_cs) &\
                                    (old_results.EdgeCS == edge_cs) &\
                                    (old_results.Policy == pol)].empty:
                            print("Skipping conf")
                            continue

                        infra = default_infra()
                        stats = _experiment(config, infra, temp_spec_file.name)
                        with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_{run_string}.json"), "w") as of:
                            stats.print(of)

                        result=dict(list(keys.items()) + list(relevant_stats_dict(stats).items()))
                        results.append(result)

                        del(stats)

                resultsDf = pd.DataFrame(results)
                if old_results is not None:
                    resultsDf = pd.concat([old_results, resultsDf])
                resultsDf.to_csv(outfile, index=False)
    
    resultsDf = pd.DataFrame(results)
    if old_results is not None:
        resultsDf = pd.concat([old_results, resultsDf])
    resultsDf.to_csv(outfile, index=False)
    print(resultsDf.groupby(["Policy", "LocalCS", "CloudCS", "EdgeCS"]).mean())

    temp_spec_file.close()

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

def experiment_varying_arrivals (args, config):
    results = []
    exp_tag = "varyingArrivals"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, str(10))
    config.set(conf.SEC_SIM, conf.RATE_UPDATE_INTERVAL, str(60))



    POLICIES = ["basic", "probabilistic2", "greedy-budget", "probabilistic"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        for policy_update_interval in [30, 60, 120, 240]:
            config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, str(policy_update_interval))
            for alpha in [0.3, 0.5, 1.0]: 
                config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, str(alpha))
                for dyn_rate_coeff in [2,5,10]:
                    for pol in POLICIES:
                        config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

                        if alpha > 0.3 and (not "probabilistic" in pol):
                            continue

                        if "greedy" in pol:
                            config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "full-knowledge")
                        else:
                            config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")


                        keys = {}
                        keys["Policy"] = pol
                        keys["Seed"] = seed
                        keys["PolicyUpdInterval"] = policy_update_interval
                        keys["Alpha"] = alpha
                        keys["DynCoeff"] = dyn_rate_coeff

                        run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                        # Check if we can skip this run
                        if old_results is not None and not\
                                old_results[(old_results.Seed == seed) &\
                                    (old_results.Alpha == alpha) &\
                                    (old_results.PolicyUpdInterval == policy_update_interval) &\
                                    (old_results.DynCoeff == dyn_rate_coeff) &\
                                    (old_results.Policy == pol)].empty:
                            print("Skipping conf")
                            continue

                        temp_spec_file = generate_spec (dynamic_rate_coeff=dyn_rate_coeff)
                        infra = default_infra()
                        stats = _experiment(config, infra, temp_spec_file.name)
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
    print(resultsDf.groupby("Policy").mean())

    temp_spec_file.close()

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

def experiment_main_comparison(args, config):
    results = []
    exp_tag = "mainComparison"
    config.set(conf.SEC_POLICY, conf.SPLIT_BUDGET_AMONG_EDGE_NODES, "false")
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")


    POLICIES = ["random", "basic", "basic-edge", "basic-budget", "probabilistic", "probabilistic2", "greedy", "greedy-min-cost", "greedy-budget"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        for latency in [0.050, 0.100, 0.200]:
            for budget in [0.25, 0.5, 1,2,10]:
                config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, str(budget))
                for functions in range(1,6):
                    for pol in POLICIES:
                        config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

                        if "greedy" in pol:
                            config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "full-knowledge")
                        else:
                            config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")


                        keys = {}
                        keys["Policy"] = pol
                        keys["Seed"] = seed
                        keys["Functions"] = functions
                        keys["Latency"] = latency
                        keys["Budget"] = budget

                        run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                        # Check if we can skip this run
                        if old_results is not None and not\
                                old_results[(old_results.Seed == seed) &\
                                    (old_results.Latency == latency) &\
                                    (old_results.Functions == functions) &\
                                    (old_results.Budget == budget) &\
                                    (old_results.Policy == pol)].empty:
                            print("Skipping conf")
                            continue

                        temp_spec_file = generate_spec (n_functions=functions)
                        infra = default_infra(edge_cloud_latency=latency)
                        stats = _experiment(config, infra, temp_spec_file.name)
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
    print(resultsDf.groupby("Policy").mean())

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

def experiment_arrivals_to_all (args, config):
    results = []
    exp_tag = "mainComparisonArvAll"
    config.set(conf.SEC_POLICY, conf.SPLIT_BUDGET_AMONG_EDGE_NODES, "true")
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")


    POLICIES = ["random", "basic", "basic-edge", "basic-budget", "probabilistic", "probabilistic2", "greedy", "greedy-min-cost", "greedy-budget"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        for latency in [0.050, 0.100, 0.200]:
            for budget in [1,2,10,20]:
                config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, str(budget))
                for pol in POLICIES:
                    config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

                    if "greedy" in pol:
                        config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "full-knowledge")
                    else:
                        config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")


                    keys = {}
                    keys["Policy"] = pol
                    keys["Seed"] = seed
                    keys["Latency"] = latency
                    keys["Budget"] = budget

                    run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                    # Check if we can skip this run
                    if old_results is not None and not\
                            old_results[(old_results.Seed == seed) &\
                                (old_results.Latency == latency) &\
                                (old_results.Budget == budget) &\
                                (old_results.Policy == pol)].empty:
                        print("Skipping conf")
                        continue

                    temp_spec_file = generate_spec (n_functions=5, arrivals_to_single_node=False)
                    infra = default_infra(edge_cloud_latency=latency)
                    stats = _experiment(config, infra, temp_spec_file.name)
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
    print(resultsDf.groupby("Policy").mean())

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

def experiment_edge (args, config):
    results = []
    exp_tag = "edge"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_SIM, conf.EDGE_EXPOSED_FRACTION, "1.0")
    config.set(conf.SEC_SIM, conf.EDGE_NEIGHBORS, "100")
    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")
    config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")


    POLICIES = ["basic", "basic-edge", "probabilistic", "probabilistic2"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, "1")

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        for latency in [0.100, 0.200]:
            for n_edges in [1, 2, 5, 10, 20]:
                for pol in POLICIES:
                    config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

                    keys = {}
                    keys["Policy"] = pol
                    keys["Seed"] = seed
                    keys["Latency"] = latency
                    keys["EdgeNodes"] = n_edges

                    run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                    # Check if we can skip this run
                    if old_results is not None and not\
                            old_results[(old_results.Seed == seed) &\
                                (old_results.Latency == latency) &\
                                (old_results.EdgeNodes == n_edges) &\
                                (old_results.Policy == pol)].empty:
                        print("Skipping conf")
                        continue

                    temp_spec_file = generate_spec (n_edges=n_edges)
                    infra = default_infra(edge_cloud_latency=latency)
                    stats = _experiment(config, infra, temp_spec_file.name)
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
    print(resultsDf.groupby("Policy").mean())

    with open(os.path.join(DEFAULT_OUT_DIR, f"{exp_tag}_conf.ini"), "w") as of:
        config.write(of)

def experiment_simple (args, config):
    results = []
    exp_tag = "simple"
    outfile=os.path.join(DEFAULT_OUT_DIR,f"{exp_tag}.csv")

    config.set(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY, "pacs")
    config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "120")
    config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "0.3")


    POLICIES = ["basic", "basic-edge", "basic-budget", "probabilistic", "probabilistic2", "greedy", "greedy-min-cost", "greedy-budget"]

    # Check existing results
    old_results = None
    if not args.force:
        try:
            old_results = pd.read_csv(outfile)
        except:
            pass

    config.set(conf.SEC_POLICY, conf.HOURLY_BUDGET, "1")

    for seed in SEEDS:
        config.set(conf.SEC_SIM, conf.SEED, str(seed))
        for cloud_speedup in [1.0, 1.5, 2.0, 4.0]:
            for cloud_cost in [0.00001, 0.00005, 0.0001, 0.001]:
                for load_coeff in [0.5, 1, 2, 4, 8]:
                    for pol in POLICIES:
                        config.set(conf.SEC_POLICY, conf.POLICY_NAME, pol)

                        if "greedy" in pol:
                            config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "full-knowledge")
                        else:
                            config.set(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, "naive-per-function")


                        keys = {}
                        keys["Policy"] = pol
                        keys["Seed"] = seed
                        keys["CloudCost"] = cloud_cost
                        keys["CloudSpeedup"] = cloud_speedup
                        keys["Load"] = load_coeff

                        run_string = "_".join([f"{k}{v}" for k,v in keys.items()])

                        # Check if we can skip this run
                        if old_results is not None and not\
                                old_results[(old_results.Seed == seed) &\
                                    (old_results.CloudSpeedup == cloud_speedup) &\
                                    (old_results.CloudCost == cloud_cost) &\
                                    (old_results.Load == load_coeff) &\
                                    (old_results.Policy == pol)].empty:
                            print("Skipping conf")
                            continue

                        temp_spec_file = generate_spec (load_coeff=load_coeff, cloud_cost=cloud_cost, cloud_speedup=cloud_speedup)
                        infra = default_infra()
                        stats = _experiment(config, infra, temp_spec_file.name)
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
    print(resultsDf.groupby("Policy").mean())

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


    POLICIES = ["probabilistic", "probabilistic2"]

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

                    temp_spec_file = generate_spec (n_functions=functions, n_classes=n_classes)
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
    config.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, str(DEFAULT_DURATION))

    if args.debug:
        args.force = True
        SEEDS=SEEDS[:1]

    if args.seed is not None:
        SEEDS = [int(args.seed)]
    
    if args.experiment.lower() == "a":
        experiment_main_comparison(args, config)
    elif args.experiment.lower() == "b":
        experiment_arrivals_to_all(args, config)
    elif args.experiment.lower() == "c":
        experiment_cold_start(args, config)
    elif args.experiment.lower() == "c2":
        experiment_cold_start2(args, config)
    elif args.experiment.lower() == "v":
        experiment_varying_arrivals(args, config)
    elif args.experiment.lower() == "e":
        experiment_edge(args, config)
    elif args.experiment.lower() == "s":
        experiment_scalability(args, config)
    elif args.experiment.lower() == "x":
        experiment_simple(args, config)
    else:
        print("Unknown experiment!")
        exit(1)
