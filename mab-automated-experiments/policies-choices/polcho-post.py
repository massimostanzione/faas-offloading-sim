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
from _internal.experiment import write_custom_configfile
from main import main

to_be_executed = []
EXPNAME = "policies-choices"
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


    graphs_ctr = -1

    with open(paramfile, 'r') as f:
        data = json.load(f)

        strategy_map = {value: index for index, value in enumerate(strategies)}
        axis_pre_map = {value: index for index, value in enumerate(axis_pre)}
        axis_post_map = {value: index for index, value in enumerate(axis_post)}

        def custom_sort_key(obj):
            return (
                strategy_map.get(obj.get("strategy"), float('inf')),  # Default a inf se non trovato
                axis_pre_map.get(obj.get("axis_pre"), float('inf')),  # Default a inf se non trovato
                axis_post_map.get(obj.get("axis_post"), float('inf'))  # Default a inf se non trovato
            )

        # Ordinamento dei dati
        data = sorted(data, key=custom_sort_key)

        for d in data:
            #for strat in strategies:
                #for ax_pre in axis_pre:
                    #for ax_post in axis_post:
                        #if d["strategy"] == strat and d["axis_pre"] == ax_pre and d["axis_post"] == ax_post:
            strat=d["strategy"]
            ax_pre=d["axis_pre"]
            ax_post=d["axis_post"]
            print(strat, ax_pre, ax_post)
            params=d["parameters"]
            mabfile = generate_outfile_name(
                consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
                list(params.keys()),
                list(params.values())
            ) + consts.SUFFIX_MABSTATSFILE
            with open(mabfile, 'r') as f:
                data = json.load(f)
            pol_fr_prev = {"random-lb": 0, "round-robin-lb": 0, "mama-lb": 0, "const-hash-lb": 0,
                           "wrr-speedup-lb": 0,
                           "wrr-memory-lb": 0, "wrr-cost-lb": 0}
            time_frames=[]
            policies=[]
            rewards=[]
            for dd in data:
                #print(d)
                # todo pre/post if d['time'] < 9000:
                pol_fr_prev[dd['policy']] += 1
                time_frames.append(dd['time'])
                policies.append(dd['policy'])
                rewards.append(dd['reward'])
            fig =  plot_rewards(time_frames, rewards, policies, strat+" "+ax_pre+" "+ax_post)

            graphs_ctr += 1
            fig.savefig(os.path.join(SCRIPT_DIR, "results",
                                     consts.DELIMITER_HYPHEN.join(
                                         [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                                    '-') + ".svg"))
            fig.clf()



if __name__ == "__main__":
    mainn()