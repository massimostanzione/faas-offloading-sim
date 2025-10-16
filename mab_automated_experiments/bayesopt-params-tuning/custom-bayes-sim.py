import datetime
import itertools
import json
import multiprocessing
import os
import sys
from json import JSONDecodeError
from multiprocessing import Pool
from pathlib import Path

from bayes_opt import BayesianOptimization

import conf
from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from mab_automated_experiments._internal.experiment import generate_outfile_name
from mab_automated_experiments._internal.experiment import write_custom_configfile
from mab_automated_experiments._internal import consts
from main import main

manager = multiprocessing.Manager()
jsondata = manager.list()

def obj_ucbtuned(ef, strat, ax_pre, ax_post, seed):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}\n")
    for _ in range(num_simulations):
        write_custom_configfile(EXPNAME, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR], [ef], seed
        ) + consts.SUFFIX_MABSTATSFILE

    return compute_total_reward(mabfile, statsfile, strat, ax_pre, ax_post) / num_simulations


def obj_ucb2(ef, alpha, strat, ax_pre, ax_post, seed):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, alpha={alpha}\n")
    for _ in range(num_simulations):
        write_custom_configfile(EXPNAME, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
                                [ef, alpha], seed)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA], [ef, alpha], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA],
            [ef, alpha], seed
        ) + consts.SUFFIX_MABSTATSFILE

        return compute_total_reward(mabfile, statsfile, strat, ax_pre, ax_post) / num_simulations


def obj_klucb(ef, c, strat, ax_pre, ax_post, seed):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, ef={ef}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(EXPNAME, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C],
                                       [ef, c], seed)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_UCB_EXPLORATION_FACTOR, MAB_KL_UCB_C], [ef, c], seed
        ) + consts.SUFFIX_MABSTATSFILE

    return compute_total_reward(mabfile, statsfile, strat, ax_pre, ax_post) / num_simulations

def obj_klucbsp(c, strat, ax_pre, ax_post, seed):
    print(f"computing for {strat}, {ax_pre} > {ax_post}, seed={seed}, c={c}\n")
    for _ in range(num_simulations):
        path = write_custom_configfile(EXPNAME, strat, ax_pre, ax_post, [MAB_KL_UCB_C],
                                       [c], seed)

        statsfile = generate_outfile_name(
            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c], seed
        ) + consts.SUFFIX_STATSFILE
        mabfile = generate_outfile_name(
            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post, [MAB_KL_UCB_C], [c], seed
        ) + consts.SUFFIX_MABSTATSFILE

    return compute_total_reward(mabfile, statsfile, strat, ax_pre, ax_post) / num_simulations


def compute_total_reward(mabfile, statsfile, strat, ax_pre, ax_post):
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

    configname = EXPNAME + "/results/" + consts.PREFIX_CONFIGFILE + "-pid" + str(os.getpid())+consts.SUFFIX_CONFIGFILE
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

def _parall_run(params):
    selected_obj_fn = None
    for stratp, ax_prep, ax_postp, seed in params:
        strat=stratp
        ax_pre=ax_prep
        ax_post=ax_postp


        def objwrapper_ucbtuned(ef):
            return obj_ucbtuned(ef, strat, ax_pre, ax_post, seed)

        def objwrapper_ucb2(ef, alpha):
            return obj_ucb2(ef, alpha, strat, ax_pre, ax_post, seed)

        def objwrapper_klucb(ef, c):
            return obj_klucb(ef, c, strat, ax_pre, ax_post, seed)

        def objwrapper_klucbsp(c):
            return obj_klucbsp(c, strat, ax_pre, ax_post, seed)

        print(f"Processing strategy={strat}, seed={seed}")
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
        elif strat == "KL-UCBsp" or strat == "KL-UCBspold":
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
        valprint = {key: float(value) for key, value in optimizer.max['params'].items()}

        data = {}
        data["strategy"]=strat
        data["axis_pre"]=ax_pre
        data["axis_post"]=ax_post
        data["parameters"] = valprint
        data["seed"] = seed
        jsondata.append(data)
        # write to text file (human-readable)

        output_file_hr = (EXPNAME + "/results/output-humanreadable")
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


if __name__ == "__main__":
    timestamp = datetime.datetime.now().replace(microsecond=0)
    path = os.path.abspath("")
    config = conf.parse_config_file(path + "/bayesopt-params-tuning/" + consts.EXPCONF_FILE)
    rundup = config["output"]["run-duplicates"]
    EXPNAME = config["experiment"]["name"]
    strategies = config["strategies"]["strategies"].split(consts.DELIMITER_COMMA)
    axis_pre = config["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
    axis_post = config["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
    ef_lower = config["parameters"]["ef-lower"]
    ef_upper = config["parameters"]["ef-upper"]
    seeds = config["parameters"]["seeds"].split(consts.DELIMITER_COMMA)
    num_simulations = config.getint("parameters", "objfn-stabilizations-iterations")

    # qui gestito custom
    max_parallel_executions = config.getint("experiment", "max-parallel-execution")

    # iterate among {strategies x axis_pre x axis_post}
    all_combinations = list(itertools.product(strategies, axis_pre, axis_post, seeds))
    chunk_size = len(all_combinations) // max_parallel_executions + (len(all_combinations) % max_parallel_executions > 0)
    chunks = [all_combinations[i:i + chunk_size] for i in range(0, len(all_combinations), chunk_size)]
    output_file_mp = (EXPNAME + "/results/output.json")

    # the parallel run
    with Pool(processes=max_parallel_executions) as pool:
        pool.map(_parall_run, chunks)

    with open(output_file_mp, "w") as mp_file:
        #mp_file.write("[\n")
        json.dump(list(jsondata), mp_file, indent=4, ensure_ascii=False)