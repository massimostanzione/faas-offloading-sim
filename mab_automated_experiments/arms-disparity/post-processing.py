import json
import os
import sys
from datetime import datetime

import numpy as np

import conf
from conf import MAB_KL_UCB_C, MAB_UCB2_ALPHA, MAB_UCB_EXPLORATION_FACTOR

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from mab_automated_experiments._internal.experiment import generate_outfile_name
from mab_automated_experiments._internal.experiment import extract_strategy_params_from_config
from mab_automated_experiments._internal.experiment import MABExperiment_IterableParam
from mab_automated_experiments._internal import consts
from mab_automated_experiments._internal.graphs import plot_arms_disparity

EXPNAME = "arms-disparity"
EXPCONF_PATH = os.path.join(EXPNAME, consts.EXPCONF_FILE)

timestamp = datetime.now().replace(microsecond=0)
expconfig = conf.parse_config_file(EXPCONF_PATH)

# BEWARE: not parameterized!
policies_no = 7  # len(config[SEC_MAB][MAB_LB_POLICIES].split(consts.DELIMITER_COMMA))
choices_no = 96  # config.getint(conf.SEC_SIM, CLOSE_DOOR_TIME) - config.getint(SEC_MAB, STAT_PRINT_INTERVAL)

expconfig = conf.parse_config_file(EXPCONF_PATH)

strategies = expconfig["strategies"]["strategies"].split(consts.DELIMITER_COMMA)

axis_pre = expconfig["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
axis_post = expconfig["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
seeds = expconfig["parameters"]["seeds"].split(consts.DELIMITER_COMMA)

global graphs_ctr

# workaround for KL-UCB: output with all the collected parameters is difficult to be analyzed
def _simplify_klucb_output():
    return MABExperiment_IterableParam(MAB_KL_UCB_C, 2.5, 2.5, 7.5)

def stationary():
    global graphs_ctr
    for seed in seeds:
        for strat in strategies:
            exploration_factor, other_strategy_params = extract_strategy_params_from_config(expconfig, strat)
            efrange = np.arange(exploration_factor.start, exploration_factor.step + exploration_factor.end,
                                exploration_factor.step)
            glob_var_coeff = {}
            for ax_pre in axis_pre:
                for other_param in other_strategy_params or [1]:
                    other_param_name = other_param.name if other_strategy_params else ""

                    # workaround for KL-UCB (see function)
                    if strat=="KL-UCB" and other_param_name==MAB_KL_UCB_C:
                        other_param=_simplify_klucb_output()

                    pstart = other_param.start if other_strategy_params else 1
                    pstart = other_param.start if other_strategy_params else 1
                    pstep = other_param.step if other_strategy_params else 1
                    pend = other_param.end if other_strategy_params else 1
                    print(strat, other_param_name, pend)
                    prange = np.arange(pstart, pstep + pend, pstep)
                    for other_param_iter in prange:
                        ax_post = ax_pre
                        local_var_coeff = []
                        for ef_iter in efrange:
                            paramnames = [exploration_factor.name]
                            paramvalues = [ef_iter]
                            if other_strategy_params:
                                paramnames.append(other_param_name)
                                paramvalues.append(other_param_iter)
                            mabfile = (generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
                                                             paramnames,
                                                             paramvalues, seed)
                                       + consts.SUFFIX_MABSTATSFILE)
                            with open(mabfile, 'r') as f:
                                data = json.load(f)

                            policies_freqs = {"random-lb": 0, "round-robin-lb": 0, "mama-lb": 0, "const-hash-lb": 0,
                                              "wrr-speedup-lb": 0,
                                              "wrr-memory-lb": 0, "wrr-cost-lb": 0}
                            for d in data:
                                # todo pre/post if d['time'] < 9000:
                                policies_freqs[d['policy']] += 1
                            vals = []
                            for value in policies_freqs.values():
                                vals.append(value)
                            var_coeff = np.std(vals) / np.average(vals)
                            local_var_coeff.append(var_coeff)
                        suffix = "" if other_param_name == "" or strat == "KL-UCBsp" else (
                                    f", {(other_param_name)}=" + str(other_param_iter))
                        glob_var_coeff[consts.get_axis_name_hr(ax_pre) + suffix] = {
                            "x": efrange,
                            "y": local_var_coeff}

            var_coeff_max = _compute_var_coeff_max()
            fig = plot_arms_disparity(glob_var_coeff, strat, True, [exploration_factor.start, exploration_factor.end],
                                      var_coeff_max)

            graphs_ctr += 1
            fig.savefig(os.path.join(SCRIPT_DIR, "results",
                                     consts.DELIMITER_HYPHEN.join([str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                                                             consts.DELIMITER_HYPHEN) + consts.SUFFIX_GRAPHFILE))
            fig.clf()

def nonstationary():
    global graphs_ctr
    for seed in seeds:
        for strat in strategies:
            exploration_factor, other_strategy_params = extract_strategy_params_from_config(expconfig, strat)
            efrange = np.arange(exploration_factor.start, exploration_factor.step + exploration_factor.end,
                                exploration_factor.step)
            glob_var_coeff = {}
            for ax_pre in axis_pre:
                for other_param in other_strategy_params or [1]:
                    other_param_name = other_param.name if other_strategy_params else ""

                    # workaround for KL-UCB (see function)
                    if strat=="KL-UCB" and other_param_name==MAB_KL_UCB_C:
                        other_param=_simplify_klucb_output()

                    pstart = other_param.start if other_strategy_params else 1
                    pstep = other_param.step if other_strategy_params else 1
                    pend = other_param.end if other_strategy_params else 1
                    prange = np.arange(pstart, pstep + pend, pstep)
                    for other_param_iter in prange:
                        for ax_post in axis_post:
                            local_var_coeff = []
                            for ef_iter in efrange:
                                paramnames = [exploration_factor.name]
                                paramvalues = [ef_iter]
                                if other_strategy_params:
                                    paramnames.append(other_param_name)
                                    paramvalues.append(other_param_iter)
                                mabfile = (generate_outfile_name(consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
                                                                 paramnames,
                                                                 paramvalues, seed)
                                           + consts.SUFFIX_MABSTATSFILE)
                                with open(mabfile, 'r') as f:
                                    data = json.load(f)

                                policies_freqs = {"random-lb": 0, "round-robin-lb": 0, "mama-lb": 0, "const-hash-lb": 0,
                                                  "wrr-speedup-lb": 0,
                                                  "wrr-memory-lb": 0, "wrr-cost-lb": 0}
                                for d in data:
                                    # todo pre/post if d['time'] < 9000:
                                    policies_freqs[d['policy']] += 1
                                vals = []
                                for value in policies_freqs.values():
                                    vals.append(value)
                                var_coeff = np.std(vals) / np.average(vals)
                                local_var_coeff.append(var_coeff)
                            suffix = "" if other_param_name == "" or strat == "KL-UCBsp" else (
                                        f", {(other_param_name)}=" + str(other_param_iter))
                            glob_var_coeff[r"$\rightarrow$ " + consts.get_axis_name_hr(ax_post) + suffix] = {
                                "x": efrange,
                                "y": local_var_coeff}

                var_coeff_max = _compute_var_coeff_max()
                fig = plot_arms_disparity(glob_var_coeff, strat, False, [exploration_factor.start, exploration_factor.end], var_coeff_max,
                                          consts.get_axis_name_hr(ax_pre))

                graphs_ctr += 1
                fig.savefig(os.path.join(SCRIPT_DIR, "results",
                                         consts.DELIMITER_HYPHEN.join([str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                                                                 consts.DELIMITER_HYPHEN) + consts.SUFFIX_GRAPHFILE))
                fig.clf()



def _compute_var_coeff_max():
    list_limit = [1 for i in range(0, policies_no - 1)]
    list_limit.append(choices_no - (policies_no))
    print(list_limit)
    return np.std(list_limit) / np.average(list_limit)

if __name__ == "__main__":
    graphs_ctr = -1
    stationary()
    nonstationary()
