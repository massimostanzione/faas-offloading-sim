import datetime
import json
import math
import multiprocessing
import os
import shutil
from copy import deepcopy
from typing import List
from typing_extensions import deprecated

# esterno
from bayes_opt import BayesianOptimization

import conf
from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C
from main import main
from rt import RealTimeTracker
from . import consts
from .consts import RundupBehavior
from .experiment import write_custom_configfile
from .logging import MABExperimentInstanceRecord, IncrementalLogger, MABExperimentInstanceRecordFactory
from .parallel_runner import run_parallel_executions

tracker = None
manager = multiprocessing.Manager()
jsondata = manager.list()

logger = IncrementalLogger()
bayes_expconf = None
bayes_exp = None
num_simulations = 1


def obj_ucbtuned(expname, ef, cdt, spi, mui, instance: MABExperimentInstanceRecord, specfile, rundup, tracker):
    strat = instance.identifiers["strategy"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    mab_rtk_context_scenarios = instance.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS]
    print(f"computing for {strat}, {instance.reward_function.__str__()}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, cdt, spi, mui, instance.reward_function, [MAB_UCB_EXPLORATION_FACTOR],
                                [ef], seed, specfile,
                                mab_intermediate_sampling_update, mab_intermediate_sampling_keys,
                                mab_rtk_context_scenarios)

        statsfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                                 consts.PREFIX_STATSFILE + "-pid" + str(
                                                     os.getpid())) + consts.SUFFIX_STATSFILE)
        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {(MAB_UCB_EXPLORATION_FACTOR): float(ef)}

        ret = compute_total_reward(expname, instance_sub, rundup, tracker) / num_simulations
        os.remove(statsfile)
        return ret


def obj_ucb2(expname, ef, cdt, spi, mui, alpha, instance: MABExperimentInstanceRecord, specfile, rundup, tracker):
    strat = instance.identifiers["strategy"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    mab_rtk_context_scenarios = instance.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS]
    print(f"computing for {strat}, {instance.reward_function.__str__()}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, cdt, spi, mui, instance.reward_function,
                                [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
                                [ef, alpha], seed, specfile, mab_intermediate_sampling_update,
                                mab_intermediate_sampling_keys, mab_rtk_context_scenarios)

        statsfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                                 consts.PREFIX_STATSFILE + "-pid" + str(
                                                     os.getpid())) + consts.SUFFIX_STATSFILE)

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {(MAB_UCB_EXPLORATION_FACTOR): float(ef),
                                                  (MAB_UCB2_ALPHA): float(alpha)}
        lookup = logger.lookup(instance_sub)
        if lookup is not None: instance_sub = lookup
        ret = compute_total_reward(expname, instance_sub, rundup, tracker) / num_simulations
        os.remove(statsfile)
        return ret


@deprecated("old function, please do not use")
def obj_klucb(expname, ef, cdt, spi, mui, c, instance: MABExperimentInstanceRecord, specfile, rundup, tracker):
    strat = instance.identifiers["strategy"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    mab_rtk_context_scenarios = instance.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS]
    print(f"computing for {strat}, {instance.reward_function.__str__()}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, cdt, spi, mui, instance.reward_function,
                                       [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C],
                                       [ef, c], seed, specfile, mab_intermediate_sampling_update,
                                       mab_intermediate_sampling_keys, mab_rtk_context_scenarios)

        statsfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                                 consts.PREFIX_STATSFILE + "-pid" + str(
                                                     os.getpid())) + consts.SUFFIX_STATSFILE)

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {(MAB_UCB_EXPLORATION_FACTOR): float(ef),
                                                  (MAB_KL_UCB_C): float(c)}
        ret = compute_total_reward(expname, instance_sub, rundup, tracker) / num_simulations
        os.remove(statsfile)
        return ret


def obj_klucbsp(expname, c, cdt, spi, mui, instance: MABExperimentInstanceRecord, specfile, rundup, tracker):
    strat = instance.identifiers["strategy"]
    seed = instance.identifiers["seed"]
    mab_intermediate_sampling_update = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL]
    mab_intermediate_sampling_keys = instance.identifiers[conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS]
    mab_rtk_context_scenarios = instance.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS]
    print(f"computing for {strat}, {instance.reward_function.__str__()}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, cdt, spi, mui, instance.reward_function, [MAB_KL_UCB_C],
                                       [c], seed, specfile, mab_intermediate_sampling_update,
                                       mab_intermediate_sampling_keys, mab_rtk_context_scenarios)

        statsfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                                 consts.PREFIX_STATSFILE + "-pid" + str(
                                                     os.getpid())) + consts.SUFFIX_STATSFILE)

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {(MAB_KL_UCB_C): float(c)}
        ret = compute_total_reward(expname, instance_sub, rundup, tracker) / num_simulations
        os.remove(statsfile)
        return ret


def compute_total_reward(expname, instance_sub: MABExperimentInstanceRecord, rundup, tracker):
    total_reward = 0
    run_simulation = logger.determine_simex_behavior(instance_sub, rundup, ["rewards"])
    configname = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", expname, consts.CONFIG_FILE_PATH, consts.PREFIX_CONFIGFILE))
    configname += "-pid" + str(os.getpid()) + consts.SUFFIX_CONFIGFILE

    if run_simulation:
        main(configname, tracker)
        mabfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                               consts.PREFIX_MABSTATSFILE + "-pid" + str(
                                                   os.getpid())) + consts.SUFFIX_MABSTATSFILE)
        strat = instance_sub.identifiers["strategy"]
        ax_pre = instance_sub.identifiers["axis_pre"]
        # ax_post=instance_sub.identifiers["axis_post"]
        ax_post = instance_sub.identifiers["axis_post"]
        seed = instance_sub.identifiers["seed"]
        specfile = instance_sub.identifiers["specfile"]
        with open(mabfile, 'r') as f:
            data = json.load(f)
        rewards = []
        for d in data:
            rewards.append(d['reward'])
        f.close()

        os.remove(configname)
        os.remove(mabfile)
    else:
        rewards = instance_sub.results["rewards"]
    total_reward += sum(rewards) / len(rewards)

    return total_reward


def extract_optimal_parameters_for_instance(instance: MABExperimentInstanceRecord) -> dict:
    found = logger.lookup(instance)
    if found is None:
        print("what? should not happen here!1", instance.identifiers["specfile"])
        exit(1)
    return found.results["optimal-params"]


# punto di ingresso
def bayesopt_search(list: List[MABExperimentInstanceRecord], procs: int, expconf, exp) \
        -> List[MABExperimentInstanceRecord]:
    rundup = expconf["output"]["run-duplicates"]
    if rundup == RundupBehavior.NO.value:
        raise RuntimeError("should not launch any simulation!")
    elif rundup == RundupBehavior.SKIP_EXISTENT.value:
        filtered = logger.filter_unprocessed_instances(list, ["optimal-params"])
    else:
        filtered = list
    global bayes_expconf
    bayes_expconf = expconf
    global bayes_exp
    bayes_exp = exp
    effective_procs = max(1, min(len(filtered), procs))
    cs = max(1, math.ceil(len(filtered) / effective_procs))
    print("FILTERED", len(filtered), "EFFECTIVE", effective_procs, "CS", cs)

    run_parallel_executions(procs, filtered, _bayesopt_search_singleinstance)

    # ora raccogli tutto
    ret = []
    for instance in list:
        found = logger.lookup(instance)
        # print(found.identifiers["parameters"],found.results,"\n\n")
        if found is None:
            print("what? should not happen here!2")
            exit(1)
        # build a ready-to-be-processed instance with the optimal params
        ready = MABExperimentInstanceRecordFactory.from_identifiers_dict(found.identifiers,
                                                                         found.results["optimal-params"])

        ret.append(ready)

    tmpfldr = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_FILES_DIR))
    if os.path.exists(tmpfldr):
        shutil.rmtree(tmpfldr, ignore_errors=True)

    return ret


init_count = 0


def _bayesopt_search_singleinstance(tracker: RealTimeTracker, instance: MABExperimentInstanceRecord) -> dict:
    timestamp = datetime.datetime.now().replace(microsecond=0)
    is_init = True
    selected_obj_fn = None
    global bayes_exp
    expname = bayes_exp.name
    rundup = bayes_exp.rundup
    ef_lower = bayes_expconf["parameters"]["ef-lower"]
    ef_upper = bayes_expconf["parameters"]["ef-upper"]
    cdt = bayes_exp.close_door_time
    spi = bayes_exp.stat_print_interval
    mui = bayes_exp.mab_update_interval

    strat = instance.identifiers["strategy"]
    seed = instance.identifiers["seed"]

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    specfile = instance.identifiers["specfile"]

    def objwrapper_ucb(ef):
        if is_init:
            global init_count
            init_count += 1
            tracker.update(os.getpid(), "bayes", "INIT-" + str(init_count))
        return obj_ucbtuned(expname, ef, cdt, spi, mui, instance, specfile, rundup, tracker)

    def objwrapper_ucbtuned(ef):
        if is_init:
            global init_count
            init_count += 1
            tracker.update(os.getpid(), "bayes", "INIT-" + str(init_count))
        return obj_ucbtuned(expname, ef, cdt, spi, mui, instance, specfile, rundup, tracker)

    def objwrapper_ucb2(ef, alpha):
        if is_init:
            global init_count
            init_count += 1
            tracker.update(os.getpid(), "bayes", "INIT-" + str(init_count))
        return obj_ucb2(expname, ef, cdt, spi, mui, alpha, instance, specfile, rundup, tracker)

    def objwrapper_klucb(ef, c):
        if is_init:
            global init_count
            init_count += 1
            tracker.update(os.getpid(), "bayes", "INIT-" + str(init_count))
        return obj_klucb(expname, ef, cdt, spi, mui, c, instance, specfile, rundup, tracker)

    def objwrapper_klucbsp(c):
        if is_init:
            global init_count
            init_count += 1
            tracker.update(os.getpid(), "bayes", "INIT-" + str(init_count))
        return obj_klucbsp(expname, c, cdt, spi, mui, instance, specfile, rundup, tracker)

    print(
        f"Processing strategy={strat}, reward_fn={instance.reward_function.__str__()}, seed={seed}, specfile={specfile}")
    if strat == "UCB":
        pbounds = {'ef': (ef_lower, ef_upper)}
        selected_obj_fn = objwrapper_ucb
    elif strat == "UCBTuned" or strat == "RTK-UCBTuned":
        pbounds = {'ef': (ef_lower, ef_upper)}
        selected_obj_fn = objwrapper_ucbtuned
    elif strat == "UCB2" or strat == "RTK-UCB2" or strat == "RTK-UCB2-ER":
        pbounds = {'ef': (ef_lower, ef_upper), 'alpha': (
            bayes_expconf["parameters"]["ucb2-alpha-lower"], bayes_expconf["parameters"]["ucb2-alpha-upper"])}
        selected_obj_fn = objwrapper_ucb2
    elif strat == "KL-UCB" or strat == "RTK-KL-UCB":
        pbounds = {'ef': (ef_lower, ef_upper),
                   'c': (bayes_expconf["parameters"]["klucb-c-lower"], bayes_expconf["parameters"]["klucb-c-upper"])}
        selected_obj_fn = objwrapper_klucb
    elif strat == "KL-UCBsp" or strat == "RTK-KL-UCBsp" or strat == "RTK-KL-UCBspold":  # TODO queste assegnazioni, invece che statiche, includerle nel mab
        pbounds = {'c': (bayes_expconf["parameters"]["klucb-c-lower"], bayes_expconf["parameters"]["klucb-c-upper"])}
        selected_obj_fn = objwrapper_klucbsp
    else:
        print("what?", strat)
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
    is_init = False
    actual_iters = 0

    # iterations
    for i in range(n_iter):
        is_init = False
        tracker.update(os.getpid(), "bayes", f"{i + 1} ({i + 1 + init_points})")
        # ... e poi le iterazioni vere: la libreria è stateful, quindi tiene conto dei punti esplorativi di cui sopra
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
    instance.add_experiment_result(
        {"NOTICE": "Fictitious instance, for optimal parameters (see below) found via bayesian optimization.",
         "optimal-params": valprint})
    logger.persist(instance)

    data = {}
    data["strategy"] = strat
    data["axis_pre"] = "pre"
    data["axis_post"] = "post"
    data["parameters"] = valprint
    data["seed"] = seed
    jsondata.append(data)
    # write to text file (human-readable)

    output_file_hr = os.path.abspath(
        os.path.join(os.path.dirname(__file__), consts.STATS_FILES_DIR, consts.BAYESOPT_OUTPUT_FILE))

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
                                                                                                       strat,
                                                                                                       data["axis_pre"],
                                                                                                       data[
                                                                                                           "axis_post"],
                                                                                                       valprint, seed))

    return valprint
