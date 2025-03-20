import datetime
import json
import multiprocessing
import os
from copy import deepcopy
from typing import List

from _internal import consts
from _internal.experiment import generate_outfile_name
from _internal.experiment import write_custom_configfile, get_param_simple_name

# esterno
from bayes_opt import BayesianOptimization

from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C
from main import main
from .logging import MABExperimentInstanceRecord, IncrementalLogger

manager = multiprocessing.Manager()
jsondata = manager.list()

logger = IncrementalLogger()
bayes_expconf = None
num_simulations = 1  # config.getint("parameters", "objfn-stabilizations-iterations")


def obj_ucbtuned(expname, ef, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed, specfile)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR],
            [ef], seed) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR], [ef], seed) + consts.SUFFIX_MABSTATSFILE

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_UCB_EXPLORATION_FACTOR): float(ef)}
        return compute_total_reward(expname, instance_sub, rundup) / num_simulations


def obj_ucb2(expname, ef, alpha, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, alpha={alpha}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
                                [ef, alpha], seed, specfile)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA], [ef, alpha], seed) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA], [ef, alpha], seed) + consts.SUFFIX_MABSTATSFILE

        instance_sub = deepcopy(instance)
        instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_UCB_EXPLORATION_FACTOR): float(ef),
                                                  get_param_simple_name(MAB_UCB2_ALPHA): float(alpha)}
        lookup = logger.lookup(instance_sub)
        if lookup is not None: instance_sub = lookup
        return compute_total_reward(expname, instance_sub, rundup) / num_simulations


def obj_klucb(expname, ef, c, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C],
                                       [ef, c], seed, specfile)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
            [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed) + consts.SUFFIX_MABSTATSFILE

    instance_sub = deepcopy(instance)
    instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_UCB_EXPLORATION_FACTOR): float(ef),
                                              get_param_simple_name(MAB_KL_UCB_C): float(c)}
    return compute_total_reward(expname, instance_sub, rundup) / num_simulations


def obj_klucbsp(expname, c, instance: MABExperimentInstanceRecord, specfile, rundup):
    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c], seed, specfile)

        statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c],
            seed) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c],
            seed) + consts.SUFFIX_MABSTATSFILE
    instance_sub = deepcopy(instance)
    instance_sub.identifiers["parameters"] = {get_param_simple_name(MAB_KL_UCB_C): float(c)}
    return compute_total_reward(expname, instance_sub, rundup) / num_simulations


def compute_total_reward(expname, instance_sub: MABExperimentInstanceRecord, rundup):
    total_reward = 0
    run_simulation = logger.determine_simex_behavior(instance_sub, rundup, ["rewards"])
    configname = expname + "/results/" + consts.CONFIG_FILE + "-pid" + str(os.getpid())
    if run_simulation:
        main(configname)
        mabfile = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_stats",
                                               consts.PREFIX_MABSTATSFILE + consts.SUFFIX_MABSTATSFILE + "-pid" + str(
                                                   os.getpid())))
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

    # instance_sub.add_experiment_result({"rewards":rewards})#{"rewards":rewards})
    # logger.persist(instance_sub)
    return total_reward


# punto di ingresso
def bayesopt_search(list: List[MABExperimentInstanceRecord], procs: int, expconf) -> List[MABExperimentInstanceRecord]:
    # concentra i processi a disposizione soltanto sulle istanze che non hanno ancora i parametri ottimi
    filtered = logger.filter_unprocessed_instances(list, ["optimal-params"])
    print(filtered)
    global bayes_expconf
    bayes_expconf = expconf
    effective_procs = max(1, min(len(filtered), procs))
    with multiprocessing.Pool(processes=effective_procs) as pool:
        pool.map(_bayesopt_search_singleinstance, filtered)  # pool.join()

    # ora raccogli tutto
    ret = []
    for instance in list:
        found = logger.lookup(instance)
        if found is None:
            print("what? should not happen here!")
            exit(1)
        # build a ready-to-be-processed instance with the optimal params
        ready = MABExperimentInstanceRecord(found.identifiers["strategy"], found.identifiers["axis_pre"],
            found.identifiers["axis_post"], found.results["optimal-params"], found.identifiers["seed"],
            found.identifiers["workload"])
        ret.append(ready)
    return ret


def _bayesopt_search_singleinstance(instance: MABExperimentInstanceRecord) -> dict:
    timestamp = datetime.datetime.now().replace(microsecond=0)
    selected_obj_fn = None
    expname = bayes_expconf["experiment"]["name"]
    rundup = bayes_expconf["output"]["run-duplicates"]
    ef_lower = bayes_expconf["parameters"]["ef-lower"]
    ef_upper = bayes_expconf["parameters"]["ef-upper"]
    # for strat, axis, wlname, seed in strategies, axis_fixed, specfile, seeds:

    strat = instance.identifiers["strategy"]
    ax_pre = instance.identifiers["axis_pre"]
    ax_post = instance.identifiers["axis_post"]
    seed = instance.identifiers["seed"]

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    specfile = os.path.join(expname, "results", "spec" + instance.identifiers["workload"] + consts.SUFFIX_SPECSFILE)

    def objwrapper_ucbtuned(ef):
        return obj_ucbtuned(expname, ef, instance, specfile, rundup)

    def objwrapper_ucb2(ef, alpha):
        return obj_ucb2(expname, ef, alpha, instance, specfile, rundup)

    def objwrapper_klucb(ef, c):
        return obj_klucb(expname, ef, c, instance, specfile, rundup)

    def objwrapper_klucbsp(c):
        return obj_klucbsp(expname, c, instance, specfile, rundup)

    print(f"Processing strategy={strat}, ax_pre={ax_pre}, ax_post={ax_post}, seed={seed}, specfile={specfile}")
    if strat == "UCBTuned":
        pbounds = {'ef': (ef_lower, ef_upper)}
        selected_obj_fn = objwrapper_ucbtuned
    elif strat == "UCB2" or strat == "RTK-UCB2":
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
    # for ax_pre in axis_pre:
    # for ax_post in axis_post:
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

    # output_file_mp = (EXPNAME + "/results/output.json")

    valprint = {key: float(value) for key, value in optimizer.max['params'].items()}
    result = {}
    result["optimal-params"] = valprint
    instance.add_experiment_result({"optimal-params": valprint})
    logger.persist(instance)

    data = {}
    data["strategy"] = strat
    data["axis_pre"] = ax_pre
    data["axis_post"] = ax_post
    data["parameters"] = valprint
    data["seed"] = seed
    jsondata.append(data)
    # write to text file (human-readable)

    output_file_hr = (expname + "/results/output-humanreadable")
    needs_header = not os.path.exists(output_file_hr)

    with open(output_file_hr, "a") as mp_file:
        if needs_header:
            mp_file.write("startdate  starttim seed   sta ran min max act strategy axis_pre   > axis_post  output\n")
            mp_file.write(
                "------------------------------------------------------------------------------------------------------------------------\n")
        mp_file.write('{0:19} {10:6} {1:3} {2:3} {3:3} {4:3} {5:3} {6:8} {7:10} > {8:10} {9}\n'.format(str(timestamp),
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
