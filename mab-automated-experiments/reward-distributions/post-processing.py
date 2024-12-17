import json
import os
import sys
from datetime import datetime
from json import JSONDecodeError
from multiprocessing import Pool
from pathlib import Path

import conf
from my_plot_stats import plot_rewards

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from _internal import consts
from _internal.experiment import generate_outfile_name
from _internal.graphs import graph_rewdist

to_be_executed = []
EXPNAME = "reward-distributions"
EXPCONF_PATH = os.path.join(EXPNAME, consts.EXPCONF_FILE)

def mainn():
    timestamp = datetime.now().replace(microsecond=0)
    config = conf.parse_config_file(EXPCONF_PATH)

    paramfilecfg = config["parameters"]["optimized-params-file"]
    rundup = config["output"]["run-duplicates"]
    paramfile = os.path.abspath(os.path.join(os.path.dirname(__file__), paramfilecfg))

    max_parallel_executions = config.getint("experiment", "max-parallel-execution")

    strategies = config["strategies"]["strategies"].split(consts.DELIMITER_COMMA)

    axis_pre = config["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
    axis_post = config["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
    seeds = config["parameters"]["seeds"].split(consts.DELIMITER_COMMA)


    graphs_ctr = -1

    with open(paramfile, 'r') as f:
        data = json.load(f)

        strategy_map = {value: index for index, value in enumerate(strategies)}
        axis_pre_map = {value: index for index, value in enumerate(axis_pre)}
        axis_post_map = {value: index for index, value in enumerate(axis_post)}
        seed_post_map = {value: index for index, value in enumerate(seeds)}

        def custom_sort_key(obj):
            return (
                strategy_map.get(obj.get("strategy"), float('inf')),
                axis_pre_map.get(obj.get("axis_pre"), float('inf')),
                axis_post_map.get(obj.get("axis_post"), float('inf')),
                seed_post_map.get(obj.get("seeds"), float('inf'))
            )

        data = sorted(data, key=custom_sort_key)

        result_dict = {}
        for strat in strategies:
            for ax_pre in axis_pre:
                for ax_post in axis_post:

                    for seed in seeds:
                        time_frames = []
                        rewards = []

                        for d in data:
                            if (
                                    d["seed"] == seed
                                    and d["strategy"] == strat
                                    and d["axis_pre"] == ax_pre
                                    and d["axis_post"] == ax_post
                            ):
                                params = d["parameters"]
                                mabfile = generate_outfile_name(
                                    consts.PREFIX_MABSTATSFILE,
                                    strat,
                                    ax_pre,
                                    ax_post,
                                    list(params.keys()),
                                    list(params.values()),
                                    seed,
                                ) + consts.SUFFIX_MABSTATSFILE

                                with open(mabfile, "r") as f:
                                    #print(mabfile)
                                    data_file = json.load(f)

                                # Raccogli time_frames e rewards
                                for dd in data_file:
                                    time_frames.append(dd["time"])
                                    rewards.append(dd["reward"])
                        #todo va aggiunto l'istante di cambio asse (accorpare in grafico)
                        result_dict[seed] = {"x": time_frames, "y": rewards}
                        #print(result_dict)

                    #fig = line_graph(result_dict, title="rewards " + strat + " " + ax_pre+" -> "+ax_post)
                    fig = graph_rewdist(result_dict, strat, ax_pre, ax_post)

                    graphs_ctr += 1
                    #fig.savefig(os.path.join(SCRIPT_DIR, "results",
                    #                         consts.DELIMITER_HYPHEN.join(
                    #                             [str(timestamp), str(graphs_ctr)]).replace(' ',
                    #                                                                        '-') + ".svg"))
                    fig.clf()



if __name__ == "__main__":
    mainn()
