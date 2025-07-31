import datetime
import json
import math
import multiprocessing
import os
import shutil
from copy import deepcopy
from typing import List

import conf
from . import consts
from .experiment import write_custom_configfile, get_param_simple_name, generate_outfile_name

# esterno
from bayes_opt import BayesianOptimization

from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C, EXPIRATION_TIMEOUT, STAT_PRINT_INTERVAL
from main import main
from .logging import MABExperimentInstanceRecord, IncrementalLogger

manager = multiprocessing.Manager()
jsondata = manager.list()

logger = IncrementalLogger()
bayes_expconf = None
num_simulations = 1  # config.getint("parameters", "objfn-stabilizations-iterations")


def obj_ucbtuned(expname, ef, cdt, spi, mui, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, cdt, spi, mui, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed, specfile, mab_intermediate_sampling_update, mab_intermediate_sampling_keys)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR],
            [ef], seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR], [ef], seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_MABSTATSFILE
        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_UCB_EXPLORATION_FACTOR): float(ef)}

        ret = compute_total_reward(expname, instance_sub, rundup) / num_simulations
        # TODO codice duplicato:
        os.remove(statsfile)
        return ret

def obj_ucb2(expname, ef, cdt, spi, mui, alpha, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, alpha={alpha}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, cdt, spi, mui, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
                                [ef, alpha], seed, specfile, mab_intermediate_sampling_update, mab_intermediate_sampling_keys)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA], [ef, alpha], seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA], [ef, alpha], seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_MABSTATSFILE

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_UCB_EXPLORATION_FACTOR): float(ef),
                                                  get_param_simple_name(MAB_UCB2_ALPHA): float(alpha)}
        lookup = logger.lookup(instance_sub)
        if lookup is not None: instance_sub = lookup
        ret= compute_total_reward(expname, instance_sub, rundup) / num_simulations
        os.remove(statsfile)
        return ret


def obj_klucb(expname, ef, c, cdt, spi, mui, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, cdt, spi, mui, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C],
                                       [ef, c], seed, specfile, mab_intermediate_sampling_update, mab_intermediate_sampling_keys)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_MABSTATSFILE

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_UCB_EXPLORATION_FACTOR): float(ef),
                                                  get_param_simple_name(MAB_KL_UCB_C): float(c)}
        ret= compute_total_reward(expname, instance_sub, rundup) / num_simulations
        os.remove(statsfile)
        return ret


def obj_klucbsp(expname, c, cdt, spi, mui, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, cdt, spi, mui, ax_pre, ax_post, [MAB_KL_UCB_C], [c], seed, specfile, mab_intermediate_sampling_update, mab_intermediate_sampling_keys)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c],
            seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c],
            seed, specfile, instance.identifiers[EXPIRATION_TIMEOUT]) + consts.SUFFIX_MABSTATSFILE
        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_KL_UCB_C): float(c)}
        ret= compute_total_reward(expname, instance_sub, rundup) / num_simulations
        os.remove(statsfile)
        return ret


def compute_total_reward(expname, instance_sub: MABExperimentInstanceRecord, rundup):
    total_reward = 0
    run_simulation = logger.determine_simex_behavior(instance_sub, rundup, ["rewards"])
    #configname = consts.CONFIG_FILE_PATH + "/" + consts.CONFIG_FILE + "-pid" + str(os.getpid())
    configname = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", expname, consts.CONFIG_FILE_PATH, consts.CONFIG_FILE))
    configname += "-pid" + str(os.getpid())

    if run_simulation:
        main(configname)
        mabfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                               consts.PREFIX_MABSTATSFILE + consts.SUFFIX_MABSTATSFILE + "-pid" + str(
                                                   os.getpid())))
        strat=instance_sub.identifiers["strategy"]
        ax_pre=instance_sub.identifiers["axis_pre"]
        #ax_post=instance_sub.identifiers["axis_post"]
        ax_post=instance_sub.identifiers["axis_post"]
        seed=instance_sub.identifiers["seed"]
        specfile=instance_sub.identifiers["specfile"]
        #statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c],
        #    seed, specfile) + consts.SUFFIX_STATSFILE
        with open(mabfile, 'r') as f:
            data = json.load(f)
        rewards = []
        for d in data:
            rewards.append(d['reward'])
        f.close()

        # TODO call the GC
        os.remove(configname)
        os.remove(mabfile)
        #fixme - rimosso nelle funzioni interne
        #os.remove(statsfile)
    else:
        rewards = instance_sub.results["rewards"]
    total_reward += sum(rewards) / len(rewards)

    return total_reward


def extract_optimal_parameters_for_instance(instance:MABExperimentInstanceRecord)->dict:
    found = logger.lookup(instance)
    if found is None:
        print("what? should not happen here!1", instance.identifiers["specfile"])
        exit(1)
    return found.results["optimal-params"]

# punto di ingresso
def bayesopt_search(list: List[MABExperimentInstanceRecord], procs: int, expconf) -> List[MABExperimentInstanceRecord]:
def bayesopt_search(list: List[MABExperimentInstanceRecord], procs: int, expconf, exp) -> List[MABExperimentInstanceRecord]:
    # concentra i processi a disposizione soltanto sulle istanze che non hanno ancora i parametri ottimi
    filtered = logger.filter_unprocessed_instances(list, ["optimal-params"])
    global bayes_expconf
    bayes_expconf = expconf
    effective_procs = max(1, min(len(filtered), procs))
    cs=max(1,math.ceil(len(filtered)/effective_procs))
    with multiprocessing.Pool(processes=effective_procs) as pool:
        pool.map(_bayesopt_search_singleinstance, filtered, chunksize=cs)

    # ora raccogli tutto
    ret = []
    for instance in list:
        found = logger.lookup(instance)
        if found is None:
            print("what? should not happen here!2")
            exit(1)
        # build a ready-to-be-processed instance with the optimal params
        ready = MABExperimentInstanceRecord(found.identifiers["strategy"], found.identifiers["axis_pre"],
            found.identifiers["axis_post"], found.results["optimal-params"], found.identifiers["seed"],
            found.identifiers["workload"], found.identifiers["specfile"], found.identifiers[conf.STAT_PRINT_INTERVAL],
                                            found.identifiers["mab-update-interval"],
                                            found.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL],
                                            found.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS],
                                            found.identifiers["expiration-timeout"])
        ret.append(ready)



    # TODO garbage collector, by instance/whole folder
    tmpfldr = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_FILES_DIR))
    if os.path.exists(tmpfldr):
        # TODO codice duplicato altrove
        shutil.rmtree(tmpfldr, ignore_errors=True)

    return ret


def _bayesopt_search_singleinstance(instance: MABExperimentInstanceRecord) -> dict:
    timestamp = datetime.datetime.now().replace(microsecond=0)
    selected_obj_fn = None
    expname = bayes_expconf["experiment"]["name"]
    rundup = bayes_expconf["output"]["run-duplicates"]
    ef_lower = bayes_expconf["parameters"]["ef-lower"]
    ef_upper = bayes_expconf["parameters"]["ef-upper"]
    cdt = bayes_expconf["experiment"]["close-door-time"]
    spi = bayes_expconf["experiment"]["stat-print-interval"]
    mui = bayes_expconf["experiment"]["mab-update-interval"]
    # for strat, axis, wlname, seed in strategies, axis_fixed, specfile, seeds:

    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    specfile = instance.identifiers["specfile"]# os.path.join(expname, "results", "spec" + str(instance.identifiers["workload"]) + consts.SUFFIX_SPECSFILE)
    def objwrapper_ucbtuned(ef):
        return obj_ucbtuned(expname, ef, cdt, spi, mui, instance, specfile, rundup)

    def objwrapper_ucb2(ef, alpha):
        return obj_ucb2(expname, ef, cdt, spi, mui, alpha, instance, specfile, rundup)

    def objwrapper_klucb(ef, c):
        return obj_klucb(expname, ef, cdt, spi, mui, c, instance, specfile, rundup)

    def objwrapper_klucbsp(c):
        return obj_klucbsp(expname, c, cdt, spi, mui, instance, specfile, rundup)

    print(f"Processing strategy={strat}, ax_pre={ax_pre}, ax_post={ax_post}, seed={seed}, specfile={specfile}")
    if strat == "UCBTuned" or strat == "RTK-UCBTuned":
        pbounds = {'ef': (ef_lower, ef_upper)}
        selected_obj_fn = objwrapper_ucbtuned
    elif strat == "UCB2" or strat == "RTK-UCB2" or strat == "RTK-UCB2-ER":
        pbounds = {'ef': (ef_lower, ef_upper), 'alpha': (
        bayes_expconf["parameters"]["ucb2-alpha-lower"], bayes_expconf["parameters"]["ucb2-alpha-upper"])}
        selected_obj_fn = objwrapper_ucb2
    elif strat == "KL-UCB":
        pbounds = {'ef': (ef_lower, ef_upper),
                   'c': (bayes_expconf["parameters"]["klucb-c-lower"], bayes_expconf["parameters"]["klucb-c-upper"])}
        selected_obj_fn = objwrapper_klucb
    elif strat == "KL-UCBsp":
        pbounds = {'c': (bayes_expconf["parameters"]["klucb-c-lower"], bayes_expconf["parameters"]["klucb-c-upper"])}
        selected_obj_fn = objwrapper_klucbsp
    else:
        print("what?")
        exit(1)
    threshold = bayes_expconf.getfloat("parameters", "improvement-threshold")
    window_size = bayes_expconf.getint("parameters", "sliding-window-size")
    improvements = []
    optimizer = BayesianOptimization(f=selected_obj_fn, pbounds=pbounds, verbose=2, random_state=1, )
    best_value = float('-inf')
    init_points = bayes_expconf.getint("parameters", "rand-points")
    n_iter = bayes_expconf.getint("parameters", "iterations")

    # init points
    optimizer.maximize(init_points=init_points, n_iter=0)
    actual_iters = 0

    # iterations
    for i in range(n_iter):
        optimizer.maximize(init_points=0, n_iter=1)

        current_best = optimizer.max["target"]
        improvement = current_best - best_value

        # sliding window for the improvements
        if len(improvements) >= window_size:
            improvements.pop(0)
        improvements.append(improvement)

        # check convergence, according to window size
        if len(improvements) == window_size and sum(improvements) / window_size < threshold:
            actual_iters = i + 1
            print(f"Convergence obtained after {actual_iters} iterations.")
            break

        actual_iters = i
        best_value = current_best


    valprint = {key: float(value) for key, value in optimizer.max['params'].items()}
    result = {}
    result["optimal-params"] = valprint
    instance.add_experiment_result({"NOTICE": "Fictitious instance, for optimal parameters (see below) found via bayesian optimization.",
                                    "optimal-params": valprint})
    logger.persist(instance)

    data = {}
    data["strategy"] = strat
    data["axis_pre"] = ax_pre
    data["axis_post"] = ax_post
    data["parameters"] = valprint
    data["seed"] = seed
    jsondata.append(data)
    # write to text file (human-readable)


    output_file_hr = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.STATS_FILES_DIR, consts.BAYESOPT_OUTPUT_FILE))

    needs_header = not os.path.exists(output_file_hr)

    with open(output_file_hr, "a+") as mp_file:
        if needs_header:
            mp_file.write("startdate  starttim seed      sta ran min max act strategy axis_pre   > axis_post  output\n")
            mp_file.write(
                "------------------------------------------------------------------------------------------------------------------------\n")
        mp_file.write('{0:19} {10:9} {1:3} {2:3} {3:3} {4:3} {5:3} {6:8} {7:10} > {8:10} {9}\n'.format(str(timestamp),
                                                                                                       bayes_expconf.getint(
                                                                                                           "parameters",
                                                                                                           "objfn-stabilizations-iterations"),
                                                                                                       bayes_expconf.getint(
                                                                                                           "parameters",
                                                                                                           "rand-points"),
                                                                                                       window_size,
                                                                                                       bayes_expconf.getint(
                                                                                                           "parameters",
                                                                                                           "iterations"),
                                                                                                       actual_iters,
                                                                                                       strat, ax_pre,
                                                                                                       ax_post,
                                                                                                       valprint, seed))

    return valprint
