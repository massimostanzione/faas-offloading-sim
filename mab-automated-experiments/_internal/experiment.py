import collections
import configparser
import itertools
import json
import os
import re
from json import JSONDecodeError
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List

import numpy as np

import conf
from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C
from main import main
from . import consts


def write_custom_configfile(expname: str, strategy: str, axis_pre: str, axis_post: str, params_names: List[str],
                            params_values: List[float], seed:int, specfile:str=None):
    outfile_stats = generate_outfile_name(consts.PREFIX_STATSFILE, strategy, axis_pre, axis_post, params_names,
                                          params_values, seed) + consts.SUFFIX_STATSFILE
    outfile_mabstats = generate_outfile_name(consts.PREFIX_MABSTATSFILE, strategy, axis_pre, axis_post, params_names,
                                             params_values, seed) + consts.SUFFIX_MABSTATSFILE

    outconfig = configparser.ConfigParser()

    # other
    outconfig.add_section(conf.SEC_SIM)
    outconfig.set(conf.SEC_SIM, conf.SPEC_FILE, "spec.yml" if specfile is None else specfile)
    outconfig.set(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, str(360))
    outconfig.set(conf.SEC_SIM, conf.STAT_PRINT_FILE, outfile_stats)
    outconfig.set(conf.SEC_SIM, "mab-stats-print-file", outfile_mabstats)
    outconfig.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, str(28800))
    outconfig.set(conf.SEC_SIM, conf.PLOT_RESP_TIMES, "false")
    outconfig.set(conf.SEC_SIM, conf.SEED, str(seed))
    outconfig.set(conf.SEC_SIM, conf.EDGE_EXPOSED_FRACTION, str(0.25))
    outconfig.add_section(conf.SEC_POLICY)
    outconfig.set(conf.SEC_POLICY, conf.POLICY_NAME, "basic")
    outconfig.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, str(0.3))
    outconfig.add_section(conf.SEC_LB)
    outconfig.set(conf.SEC_LB, conf.LB_POLICY, "random-lb")

    outconfig.add_section(conf.SEC_MAB)
    outconfig.set(conf.SEC_MAB, conf.MAB_UPDATE_INTERVAL, str(300))
    outconfig.set(conf.SEC_MAB, conf.MAB_NON_STATIONARY_ENABLED, "false" if axis_pre == axis_post else "true")
    outconfig.set(conf.SEC_MAB, conf.MAB_LB_POLICIES,
                  "random-lb, round-robin-lb, mama-lb, const-hash-lb, wrr-speedup-lb, wrr-memory-lb, wrr-cost-lb")
    outconfig.set(conf.SEC_MAB, conf.MAB_STRATEGY, strategy)

    for i, param_name in enumerate(params_names):
        outconfig.set(conf.SEC_MAB, get_param_full_name(param_name), str(params_values[i]))

    # stationary
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ALPHA, str(1) if axis_pre == consts.RewardFnAxis.LOADIMB.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_BETA,
                  str(1) if axis_pre == consts.RewardFnAxis.RESPONSETIME.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_GAMMA, str(1) if axis_pre == consts.RewardFnAxis.COST.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_DELTA, str(1) if axis_pre == consts.RewardFnAxis.UTILITY.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ZETA, str(1) if axis_pre == consts.RewardFnAxis.VIOLATIONS.value else str(0))

    # non-stationary
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ALPHA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.LOADIMB.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_BETA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.RESPONSETIME.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_GAMMA_POST, str(1) if axis_post == consts.RewardFnAxis.COST.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_DELTA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.UTILITY.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ZETA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.VIOLATIONS.value else str(0))
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", expname, "results", consts.CONFIG_FILE))
    config_path+="-pid"+str(os.getpid())

    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w") as of:
        outconfig.write(of)
    return config_path


class MABExperiment_IterableParam:
    def __init__(self, name: str, start: float, step: float, end: float):
        self.name = name
        self.start = start
        self.step = step
        self.end = end


def get_param_simple_name(full_name: str) -> str:
    if full_name == MAB_UCB_EXPLORATION_FACTOR:
        return "ef"
    elif full_name == MAB_UCB2_ALPHA:
        return "alpha"
    elif full_name == MAB_KL_UCB_C:
        return "c"
    return full_name

# workaround for already computed statistics
def get_param_simple_name_sort(full_name: str) -> str:
    if full_name == MAB_UCB_EXPLORATION_FACTOR:
        return "ef"
    elif full_name == MAB_UCB2_ALPHA:
        return "zalpha"
    elif full_name == MAB_KL_UCB_C:
        return "c"
    return full_name

def get_param_full_name(simple_name: str) -> str:
    if simple_name == "ef":
        return MAB_UCB_EXPLORATION_FACTOR
    elif simple_name == "alpha":
        return MAB_UCB2_ALPHA
    elif simple_name == "c":
        return MAB_KL_UCB_C
    return simple_name


def generate_outfile_name(prefix, strategy, axis_pre, axis_post, params_names, params_values, seed):

    pardict={}
    for i,_ in enumerate(params_names):
        pardict[params_names[i]]=params_values[i]
        print(get_param_simple_name(params_names[i]))
    pardict=collections.OrderedDict(sorted(pardict.items(), key=lambda item: get_param_simple_name_sort(item[0])))
    output_suffix = consts.DELIMITER_HYPHEN.join([prefix, strategy, consts.DELIMITER_AXIS.join([axis_pre, axis_post])])

    for key, value in pardict.items():
        output_suffix = consts.DELIMITER_HYPHEN.join(
            [output_suffix, consts.DELIMITER_PARAMS.join([get_param_simple_name(key), "{}".format(float(value))])])
    output_suffix=consts.DELIMITER_HYPHEN.join([output_suffix, consts.DELIMITER_PARAMS.join(["seed", seed])])
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_stats", output_suffix))
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    return config_path

def is_exploration_factor(parameter_name:str, strategy:str)->bool:
    exploration_factor_map = {
        "UCBTuned": conf.MAB_UCB_EXPLORATION_FACTOR,
        "UCB2": conf.MAB_UCB_EXPLORATION_FACTOR,
        "KL-UCB": conf.MAB_UCB_EXPLORATION_FACTOR,
        "KL-UCBsp": conf.MAB_KL_UCB_C
    }


    return exploration_factor_map[strategy]==parameter_name

def is_other_strategy_param(parameter_name:str, strategy:str)->bool:
    other_params_map = {
        "UCBTuned": [],
        "UCB2": [conf.MAB_UCB2_ALPHA],
        "KL-UCB": [conf.MAB_KL_UCB_C],
        "KL-UCBsp": []
    }
    return parameter_name in other_params_map[strategy]

def filter_strategy_params(params:List[MABExperiment_IterableParam], strategy:str) -> List[MABExperiment_IterableParam]:
    ret=[]
    for param in params:
        if is_exploration_factor(param.name, strategy) or is_other_strategy_param(param.name, strategy):
            ret.append(param)
    print(ret)
    return ret

def extract_iterable_params_from_config(expconfig) -> List[MABExperiment_IterableParam]:
    _, iterable_params=extract_strategy_params_from_config(expconfig)
    return iterable_params

def extract_strategy_params_from_config(expconfig, strategy:str=None) -> [MABExperiment_IterableParam, List[MABExperiment_IterableParam]]:

    exploration_factor=None
    other_strategy_params = []

    # fetch iterable params from expconfig via regex
    parameters_sect = expconfig["parameters"]
    fetched_params = set()
    for key in parameters_sect.keys():
        match = re.match(r"^(.*?)-(start|step|end)$", key)
        if match:
            fetched_params.add(match.group(1))

    for param_name in sorted(fetched_params):
        start = float(parameters_sect.get(f"{param_name}-start"))
        step = float(parameters_sect.get(f"{param_name}-step"))
        end = float(parameters_sect.get(f"{param_name}-end"))

        if strategy is not None:
            if is_exploration_factor(param_name, strategy):
                exploration_factor=MABExperiment_IterableParam(param_name, start, step, end)
            elif is_other_strategy_param(param_name, strategy):
                parameter = MABExperiment_IterableParam(param_name, start, step, end)
                other_strategy_params.append(parameter)
        else:
            parameter = MABExperiment_IterableParam(param_name, start, step, end)
            other_strategy_params.append(parameter)

    return exploration_factor, other_strategy_params


class MABExperiment:
    def __init__(self, name: str, strategies: List[str], axis_pre: List[str] = None, axis_post: List[str] = None,
                 params: List[MABExperiment_IterableParam] = None, graphs: List[str] = None,
                 rundup: str = consts.RundupBehavior.SKIP_EXISTENT.value,
                 max_parallel_executions: int = 1,
                 seeds:List[int]=None,
                 specfile:str=None):
        self.name = name
        self.strategies = strategies
        self.axis_pre = axis_pre
        self.axis_post = axis_post
        self.params = params
        self.graphs = graphs
        self.rundup = rundup
        self.max_parallel_executions = max_parallel_executions
        self.seeds=[123] if seeds==None else seeds
        self.specfile=specfile

    def _generate_config(self, strategy: str, axis_pre: str, axis_post: str, param_names: List[str],
                         param_values: List[float], seed:int):
        return write_custom_configfile(self.name, strategy, axis_pre, axis_post, param_names, param_values, seed, self.specfile)

    def run(self):
        print(f"Starting experiment {self.name}...")
        max_procs = self.max_parallel_executions

        # iterate among {strategies x axis_pre x axis_post}
        all_combinations = list(itertools.product(self.strategies, self.axis_pre, self.axis_post, self.seeds))
        chunk_size = len(all_combinations) // max_procs + (len(all_combinations) % max_procs > 0)
        chunks = [all_combinations[i:i + chunk_size] for i in range(0, len(all_combinations), chunk_size)]

        with Pool(processes=max_procs) as pool:
            pool.map(self._parall_run, chunks)

        # la funzione parallela
    def _parall_run(self, params):
        rundup = self.rundup
        for strategy, ax_pre, ax_post, seed in params:
            print(f"Processing strategy={strategy}, ax_pre={ax_pre}, ax_post={ax_post}, seed={seed}")
            filtered_params = filter_strategy_params(self.params, strategy)
            ranges = [np.arange(param.start, param.end + param.step, param.step) for param in filtered_params]
            param_combinations = itertools.product(*ranges)
            for combination in param_combinations:
                rounded_combination = [round(value, 2) for value in combination]
                param_names = [p.name for p in filtered_params]
                current_values = [p for p in rounded_combination]

                print()
                print("============================================")
                print(f"Running experiment \"{self.name}\"")
                print(f"with the following configuration")
                print(f"\tStrategy:\t{strategy}")
                print(f"\tAxis:\t\t{ax_pre} -> {ax_post}")
                print(f"\tSeed:\t\t{seed}")
                print(f"\tParameters:")
                for i, _ in enumerate(param_names):
                    print(f"\t\t> {param_names[i]} = {current_values[i]}")
                print("--------------------------------------------")

                path = self._generate_config(strategy, ax_pre, ax_post, param_names, current_values, seed)

                statsfile = generate_outfile_name(
                    consts.PREFIX_STATSFILE, strategy, ax_pre, ax_post, param_names, current_values, seed
                ) + consts.SUFFIX_STATSFILE

                mabfile = generate_outfile_name(
                    consts.PREFIX_MABSTATSFILE, strategy, ax_pre, ax_post, param_names, current_values, seed
                ) + consts.SUFFIX_MABSTATSFILE

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
                                print(
                                    "mab-stats file non existent or JSON parsing error, running simulation...")
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

                if run_simulation:
                    main(path)

        os.remove(path)
        print("end.")
