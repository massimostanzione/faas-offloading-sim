# TODO usare come base per l'ottimizzazione/unificazione
import datetime
import json
import multiprocessing
import os
from json import JSONDecodeError
from pathlib import Path

# esterno
from bayes_opt import BayesianOptimization

from _internal.experiment import generate_outfile_name
from _internal.experiment import write_custom_configfile

from _internal import consts

from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C
from main import main

manager = multiprocessing.Manager()
jsondata = manager.list()

num_simulations = 1#config.getint("parameters", "objfn-stabilizations-iterations")

def obj_ucbtuned(expname, ef, strat, ax_pre, ax_post, seed, specfile, rundup):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed, specfile)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed
        ) + consts.SUFFIX_MABSTATSFILE

    return compute_total_reward(expname, mabfile, statsfile, strat, ax_pre, ax_post, rundup) / num_simulations


def obj_ucb2(expname, ef, alpha, strat, ax_pre, ax_post, seed, specfile, rundup):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, alpha={alpha}\n")
    for _ in range(num_simulations):
        write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
                                [ef, alpha], seed, specfile)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA], [ef, alpha], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
            [ef, alpha], seed
        ) + consts.SUFFIX_MABSTATSFILE

        return compute_total_reward(expname, mabfile, statsfile, strat, ax_pre, ax_post, rundup) / num_simulations


def obj_klucb(expname, ef, c, strat, ax_pre, ax_post, seed, specfile, rundup):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C],
                                       [ef, c], seed, specfile)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed
        ) + consts.SUFFIX_MABSTATSFILE

    return compute_total_reward(expname, mabfile, statsfile, strat, ax_pre, ax_post, rundup) / num_simulations

def obj_klucbsp(expname, c, strat, ax_pre, ax_post, seed, specfile, rundup):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(expname, strat, ax_pre, ax_post, [MAB_KL_UCB_C],
                                       [c], seed, specfile)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c], seed
        ) + consts.SUFFIX_MABSTATSFILE

    return compute_total_reward(expname, mabfile, statsfile, strat, ax_pre, ax_post, rundup) / num_simulations


def compute_total_reward(expname, mabfile, statsfile, strat, ax_pre, ax_post, rundup):
    total_reward = 0
    run_simulation = None
    if rundup == consts.RundupBehavior.ALWAYS.value:
        run_simulation = True
    elif rundup == consts.RundupBehavior.NO.value:
        run_simulation = False
    elif rundup == consts.RundupBehavior.SKIP_EXISTENT.value:
        if Path(statsfile).exists():
            # make sure that the file is not only existent, but also not incomplete
            # (i.e. correctly JSON-readable until the EOF)
            with open(mabfile, 'r', encoding='utf-8') as r:
                try:
                    json.load(r)
                except JSONDecodeError:
                    print("mab-stats file non existent or JSON parsing error, running simulation...")
                    run_simulation = True
                else:
                    print("parseable stats- and mab-stats file found, skipping simulation.")
                    run_simulation = False
        else:
            print("stats-file non not found, running simulation...")
            run_simulation = True
    if run_simulation is None:
        print("Something is really odd...")
        exit(1)

    configname = expname + "/results/" + consts.CONFIG_FILE + "-pid" + str(os.getpid())
    if run_simulation:
        main(configname)
    os.remove(configname)
    with open(mabfile, 'r') as f:
        data = json.load(f)
    rewards = []
    for d in data:
        rewards.append(d['reward'])
    f.close()
    total_reward += sum(rewards) / len(rewards)
    return total_reward
from .logging import MABExperimentInstanceRecord
# Oss.: è per singola ricerca
def bayesopt_search(expname, strat, axis_fixed, specfile, seed, config, rundup, wl_name):
    timestamp = datetime.datetime.now().replace(microsecond=0)
    selected_obj_fn = None
    ef_lower = config["parameters"]["ef-lower"]
    ef_upper = config["parameters"]["ef-upper"]
    #for strat, axis, wlname, seed in strategies, axis_fixed, specfile, seeds:
    ax_pre=axis_fixed
    ax_post=axis_fixed
    def objwrapper_ucbtuned(ef):
        return obj_ucbtuned(expname, ef, strat, ax_pre, ax_post, seed, specfile, rundup)

    def objwrapper_ucb2(ef, alpha):
        return obj_ucb2(expname, ef, alpha, strat, ax_pre, ax_post, seed, specfile, rundup)

    def objwrapper_klucb(ef, c):
        return obj_klucb(expname, ef, c, strat, ax_pre, ax_post, seed, specfile, rundup)

    def objwrapper_klucbsp(c):
        return obj_klucbsp(expname, c, strat, ax_pre, ax_post, seed, specfile, rundup)

    print(f"Processing strategy={strat}, ax_pre={ax_pre}, ax_post={ax_post}, seed={seed}, specfile={specfile}")
    if strat == "UCBTuned":
        pbounds = {'ef': (ef_lower, ef_upper)}
        selected_obj_fn = objwrapper_ucbtuned
    elif strat == "UCB2":
        pbounds = {'ef': (ef_lower, ef_upper),
                   'alpha': (config["parameters"]["ucb2-alpha-lower"], config["parameters"]["ucb2-alpha-upper"])}
        selected_obj_fn = objwrapper_ucb2
    elif strat == "KL-UCB":
        pbounds = {'ef': (ef_lower, ef_upper),
                   'c': (config["parameters"]["klucb-c-lower"], config["parameters"]["klucb-c-upper"])}
        selected_obj_fn = objwrapper_klucb
    elif strat == "KL-UCBsp":
        pbounds = {'c': (config["parameters"]["klucb-c-lower"], config["parameters"]["klucb-c-upper"])}
        selected_obj_fn = objwrapper_klucbsp
    else:
        print("what?")
        exit(1)
    threshold = config.getfloat("parameters", "improvement-threshold")
    window_size = config.getint("parameters", "sliding-window-size")
    improvements = []
    #for ax_pre in axis_pre:
        #for ax_post in axis_post:
    optimizer = BayesianOptimization(
        f=selected_obj_fn,
        pbounds=pbounds,
        verbose=2,
        random_state=1,
    )
    best_value = float('-inf')
    init_points = config.getint("parameters", "rand-points")
    n_iter = config.getint("parameters", "iterations")

    # init points
    optimizer.maximize(init_points=init_points, n_iter=0)
    actual_iters=0

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
            actual_iters=i+1
            print(f"Convergence obtained after {actual_iters} iterations.")
            break

        actual_iters=i
        best_value = current_best

    #output_file_mp = (EXPNAME + "/results/output.json")
    instance = MABExperimentInstanceRecord(strat, axis_fixed, axis_fixed, None, seed, wl_name)

    valprint = {key: float(value) for key, value in optimizer.max['params'].items()}
    result={"optimal-params", valprint}
    instance.add_experiment_result(result)

    data = {}
    data["strategy"]=strat
    data["axis_pre"]=ax_pre
    data["axis_post"]=ax_post
    data["parameters"] = valprint
    data["seed"] = seed
    jsondata.append(data)
    # write to text file (human-readable)

    output_file_hr = (expname + "/results/output-humanreadable")
    needs_header = not os.path.exists(output_file_hr)

    with open(output_file_hr, "a") as mp_file:
        if needs_header:
            mp_file.write("startdate  starttim seed   sta ran min max act strategy axis_pre   > axis_post  output\n")
            mp_file.write("------------------------------------------------------------------------------------------------------------------------\n")
        mp_file.write('{0:19} {10:6} {1:3} {2:3} {3:3} {4:3} {5:3} {6:8} {7:10} > {8:10} {9}\n'
                   .format(str(timestamp),
                           config.getint("parameters", "objfn-stabilizations-iterations"),
                           config.getint("parameters", "rand-points"),
                           window_size,
                           config.getint("parameters", "iterations"),
                           actual_iters,
                           strat,
                           ax_pre, ax_post,
                           valprint,
                           seed
                           ))

