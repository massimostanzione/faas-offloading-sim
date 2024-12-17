import json
import os
import sys
from datetime import datetime

import numpy as np

import conf
from my_plot_stats import plot_rewards

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from _internal import consts
from _internal.experiment import generate_outfile_name
from _internal.experiment import get_param_simple_name
from _internal.graphs import graph_rewparconf

to_be_executed = []
EXPNAME = "policies-choices"
EXPCONF_PATH = os.path.join(EXPNAME, consts.EXPCONF_FILE)


def mainn():
    timestamp = datetime.now().replace(microsecond=0)
    config = conf.parse_config_file(EXPCONF_PATH)

    paramfilecfg = config["parameters"]["optimized-params-file"]
    rundup = config["output"]["run-duplicates"]

    max_parallel_executions = config.getint("experiment", "max-parallel-execution")

    strategies = config["strategies"]["strategies"].split(consts.DELIMITER_COMMA)

    axis_pre = config["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
    axis_post = config["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
    seeds = config["parameters"]["seeds"].split(consts.DELIMITER_COMMA)



    graphs_ctr=-1

    for strat in strategies:
        # ugly! argh!!!
        if strat=="UCBTuned":
            parnames=[conf.MAB_UCB_EXPLORATION_FACTOR]
            efrange=np.arange(0, 1+0.25, 0.25)
            paramrange=np.arange(0,1+1,1)
            monoparam=True
        elif strat=="UCB2":
            parnames=[conf.MAB_UCB_EXPLORATION_FACTOR, conf.MAB_UCB2_ALPHA]
            efrange=np.arange(0, 1+0.25, 0.25)
            paramrange=np.arange(0.25, 0.25+0.75, 0.25)
            monoparam=False
        elif strat=="KL-UCB":
            parnames=[conf.MAB_UCB_EXPLORATION_FACTOR, conf.MAB_KL_UCB_C]
            efrange=np.arange(0, 1+0.25, 0.25)
            paramrange=np.arange(0, 10, 2.5+10)
            monoparam=False
        elif strat=="KL-UCBsp":
            parnames=[conf.MAB_KL_UCB_C]
            efrange=np.arange(0, 2.5+10, 2.5)
            paramrange=np.arange(0,1+1,1)
            monoparam=True

        series={}
        for ax_pre in axis_pre:
            for ax_post in axis_post:
                for seed in seeds:
                    for ef in efrange:
                        for param in paramrange:
                            print(strat, ax_pre, ax_post, ef, param)
                            parnamelist=[ef]
                            mabfile = generate_outfile_name(
                                consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
                                [parnames[0], parnames[1]] if len(parnames)==2 else [parnames[0]],
                                [ef, param] if len(parnames)==2 else [ef],
                                seed
                            ) + consts.SUFFIX_MABSTATSFILE
                            print(mabfile)
                            with open(mabfile, 'r') as fmab:
                                dataaR = json.load(fmab)
                            #print(dataaR)
                            time_frames = []
                            #policies = []
                            rewards = []
                            for ddR in dataaR:
                                # print(d)
                                # todo pre/post if d['time'] < 9000:
                                #pol_fr_prev[dd['policy']] += 1
                                time_frames.append(ddR['time'])
                                rewards.append(ddR['reward'])
                            print(time_frames, rewards)
                            label=get_param_simple_name(parnames[0])+"="+str(ef)
                            if not monoparam:
                                label+=", "+get_param_simple_name(parnames[1])+"="+str(param)
                            series[label]={"x":time_frames,"y":rewards, "ax_pre":consts.get_axis_name_hr(ax_pre), "ax_post":consts.get_axis_name_hr(ax_post)}

                            if monoparam: break

                fig = graph_rewparconf(series, strat)

                graphs_ctr += 1
                fig.savefig(os.path.join(SCRIPT_DIR, "results",
                                         consts.DELIMITER_HYPHEN.join(
                                             [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                                        '-') + ".svg"),
                            bbox_inches='tight')
                fig.clf()


if __name__ == "__main__":
    mainn()
