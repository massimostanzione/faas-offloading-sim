import collections
import configparser
import itertools
import json
import math
import os
import re
import shutil
from multiprocessing.pool import Pool
from typing import List

import numpy as np

import conf
from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA, MAB_KL_UCB_C, MAB_ALL_STRATEGIES_PARAMETERS, \
    EXPIRATION_TIMEOUT, STAT_PRINT_INTERVAL
from main import main
from .logging import MABExperimentInstanceRecord, IncrementalLogger, SCRIPT_DIR
from . import consts

logger = IncrementalLogger()


def write_custom_configfile(expname: str, strategy: str, close_door_time: float, stat_print_interval: float,
                            mab_update_interval: float, axis_pre: str, axis_post: str, params_names: List[str],
                            params_values: List[float], seed: int, specfile: str = None,
                            mab_intermediate_sampling_update: float = None,
                            mab_intermediate_sampling_keys=None,
                            expiration_timeout: float = consts.DEFAULT_EXPIRATION_TIMEOUT):

    if mab_intermediate_sampling_keys is None:
        mab_intermediate_sampling_keys = []
    outfile_stats = generate_outfile_name(consts.PREFIX_STATSFILE, strategy, axis_pre, axis_post, params_names,
                                          params_values, seed, specfile, expiration_timeout) + consts.SUFFIX_STATSFILE
    outfile_mabstats = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                                    consts.PREFIX_MABSTATSFILE + consts.SUFFIX_MABSTATSFILE + "-pid" + str(
                                                        os.getpid())))

    outconfig = configparser.ConfigParser()

    # other
    outconfig.add_section(conf.SEC_SIM)
    outconfig.set(conf.SEC_SIM, conf.SPEC_FILE, "../spec.yml" if specfile is None else specfile)
    outconfig.set(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, str(stat_print_interval) if stat_print_interval is not None else consts.DEFAULT_STAT_PRINT_INTERVAL)
    outconfig.set(conf.SEC_SIM, conf.STAT_PRINT_FILE, outfile_stats)
    outconfig.set(conf.SEC_SIM, "mab-stats-print-file", outfile_mabstats)
    outconfig.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, str(close_door_time))
    outconfig.set(conf.SEC_SIM, conf.PLOT_RESP_TIMES, "false")
    outconfig.set(conf.SEC_SIM, conf.SEED, str(seed))
    outconfig.set(conf.SEC_SIM, conf.EDGE_EXPOSED_FRACTION, str(0.25))
    outconfig.add_section(conf.SEC_POLICY)
    outconfig.set(conf.SEC_POLICY, conf.POLICY_NAME, "basic")
    outconfig.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, str(0.3))
    outconfig.add_section(conf.SEC_LB)
    outconfig.set(conf.SEC_LB, conf.LB_POLICY, "random-lb")

    outconfig.add_section(conf.SEC_CONTAINER)
    outconfig.set(conf.SEC_CONTAINER, conf.EXPIRATION_TIMEOUT, str(expiration_timeout))

    outconfig.add_section(conf.SEC_MAB)
    outconfig.set(conf.SEC_MAB, conf.MAB_UPDATE_INTERVAL, str(mab_update_interval))

    # intermediate sampling
    if mab_intermediate_sampling_update is not None:
        outconfig.set(conf.SEC_MAB, conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL, str(mab_intermediate_sampling_update))
        outconfig.set(conf.SEC_MAB, conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS, ','.join(mab_intermediate_sampling_keys))

    outconfig.set(conf.SEC_MAB, conf.MAB_NON_STATIONARY_ENABLED, "false" if axis_pre == axis_post else "true")
    outconfig.set(conf.SEC_MAB, conf.MAB_LB_POLICIES,
                  "random-lb, round-robin-lb, mama-lb, const-hash-lb, wrr-speedup-lb, wrr-memory-lb, wrr-cost-lb")
    outconfig.set(conf.SEC_MAB, conf.MAB_STRATEGY, strategy)

    for i, param_name in enumerate(params_names):
        outconfig.set(conf.SEC_MAB, get_param_full_name(param_name), str(params_values[i]))

    # stationary
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ALPHA,
                  str(1) if axis_pre == consts.RewardFnAxis.LOADIMB.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_BETA,
                  str(1) if axis_pre == consts.RewardFnAxis.RESPONSETIME.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_GAMMA, str(1) if axis_pre == consts.RewardFnAxis.COST.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_DELTA,
                  str(1) if axis_pre == consts.RewardFnAxis.UTILITY.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ZETA,
                  str(1) if axis_pre == consts.RewardFnAxis.VIOLATIONS.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ETA,
                  str(1) if axis_pre == consts.RewardFnAxis.COLD_STARTS.value else str(0))

    # non-stationary
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ALPHA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.LOADIMB.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_BETA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.RESPONSETIME.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_GAMMA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.COST.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_DELTA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.UTILITY.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ZETA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.VIOLATIONS.value else str(0))
    outconfig.set(conf.SEC_MAB, conf.MAB_REWARD_ETA_POST,
                  str(1) if axis_post == consts.RewardFnAxis.COLD_STARTS.value else str(0))
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", expname, consts.CONFIG_FILE_PATH, consts.CONFIG_FILE))
    config_path += "-pid" + str(os.getpid())

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
        return "alpha"
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


def generate_outfile_name(prefix, strategy, axis_pre, axis_post, params_names, params_values, seed, specfile, expiration_timeeout):
    pardict = {}
    for i, _ in enumerate(params_names):
        pardict[params_names[i]] = params_values[i]
        print(get_param_simple_name(params_names[i]))
    pardict = collections.OrderedDict(sorted(pardict.items(), key=lambda item: get_param_simple_name_sort(item[0])))
    output_suffix = consts.DELIMITER_HYPHEN.join([prefix, strategy, consts.DELIMITER_AXIS.join([axis_pre, axis_post])])

    for key, value in pardict.items():
        output_suffix = consts.DELIMITER_HYPHEN.join(
            [output_suffix, consts.DELIMITER_PARAMS.join([get_param_simple_name(key), "{}".format(float(value))])])
    output_suffix = consts.DELIMITER_HYPHEN.join([output_suffix, consts.DELIMITER_PARAMS.join(["seed", seed])])
    output_suffix = consts.DELIMITER_HYPHEN.join([output_suffix, consts.DELIMITER_PARAMS.join(["specfile", specfile])])
    output_suffix = consts.DELIMITER_HYPHEN.join([output_suffix, consts.DELIMITER_PARAMS.join(["exptimeout", str(expiration_timeeout)])])
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION, output_suffix))
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    return config_path



def _is_exploration_factor(parameter_name: str, strategy: str) -> bool:
    exploration_factor_map = {

        # non-contextual
        "UCBTuned": conf.MAB_UCB_EXPLORATION_FACTOR,
        "UCB2": conf.MAB_UCB_EXPLORATION_FACTOR,
        "KL-UCB": conf.MAB_UCB_EXPLORATION_FACTOR,
        "KL-UCBsp": conf.MAB_KL_UCB_C,

        # contextual
        "RTK-UCB2": conf.MAB_UCB_EXPLORATION_FACTOR,
        "RTK-UCB2-ER": conf.MAB_UCB_EXPLORATION_FACTOR,
        "RTK-UCBTuned": conf.MAB_UCB_EXPLORATION_FACTOR,
    }

    return exploration_factor_map[strategy] == parameter_name


def _is_other_strategy_param(parameter_name: str, strategy: str) -> bool:
    other_params_map = {

        # non-contextual
        "UCBTuned": [],
        "UCB2": [conf.MAB_UCB2_ALPHA],
        "KL-UCB": [conf.MAB_KL_UCB_C],
        "KL-UCBsp": [],

        # contextual
        "RTK-UCB2": [conf.MAB_UCB2_ALPHA],
        "RTK-UCB2-ER": [conf.MAB_UCB2_ALPHA],
        "RTK-UCBTuned": [],
    }
    return parameter_name in other_params_map[strategy]


def filter_strategy_params(params: List[MABExperiment_IterableParam], strategy: str) -> List[
    MABExperiment_IterableParam]:
    ret = []
    for param in params:
        if _is_exploration_factor(param.name, strategy) or _is_other_strategy_param(param.name, strategy):
            ret.append(param)
    print(ret)
    return ret

def _is_iterable(key):
    return re.match(r"^(.*?)-(start|step|end)$", key)

def _is_bayesopt(value):
    return value=="bayesopt"

def extract_iterable_params_from_config(expconfig) -> List[MABExperiment_IterableParam]:
    _, iterable_params = extract_strategy_params_from_config(expconfig)
    return iterable_params


def extract_strategy_params_from_config(expconfig, strategy: str = None) -> [MABExperiment_IterableParam,
                                                                             List[MABExperiment_IterableParam]]:
    exploration_factor = None
    other_strategy_params = []

    # fetch iterable params from expconfig via regex
    parameters_sect = expconfig["parameters"]
    fetched_params_fixed = set()
    fetched_params_iterable = set()
    for key in parameters_sect.keys():

        # look for fixed (i.e. non-iterable) parameters
        if key in MAB_ALL_STRATEGIES_PARAMETERS:
            fetched_params_fixed.add(key)

        # look for iterable parameters
        match = re.match(r"^(.*?)-(start|step|end)$", key)
        if match:
            fetched_params_iterable.add(match.group(1))

    # now build the parameter instances for both fixed and iterable parameters
    param_insts=[]
    for param_name in sorted(fetched_params_fixed):
        # ... treat fixed parameters as iterable ones
        start = float(parameters_sect.get(param_name))
        step = start
        end = start
        param_insts.append(MABExperiment_IterableParam(param_name, start, step, end))

    for param_name in sorted(fetched_params_iterable):
        start = float(parameters_sect.get(f"{param_name}-start"))
        step = float(parameters_sect.get(f"{param_name}-step"))
        end = float(parameters_sect.get(f"{param_name}-end"))
        param_insts.append(MABExperiment_IterableParam(param_name, start, step, end))

    for param in param_insts:
        if strategy is not None:
            if _is_exploration_factor(param.name, strategy):
                exploration_factor = param
            elif _is_other_strategy_param(param.name, strategy):
                other_strategy_params.append(param)
        else:
            other_strategy_params.append(param)

    return exploration_factor, other_strategy_params


from .bayesopt import bayesopt_search

class MABExperiment:
    def __init__(self, expconf, name: str, strategies: List[str], close_door_time: float = 28800,
                 stat_print_interval: float = 360, mab_update_interval: float = 300,
                 mab_intermediate_sampling_update_interval:float=None,
                 mab_intermediate_samples_keys:List[str]=None,
                 axis_pre: List[str] = None,
                 axis_post: List[str] = None,
                 iterable_params: List[MABExperiment_IterableParam] = None, graphs: List[str] = None,
                 rundup: str = consts.RundupBehavior.SKIP_EXISTENT.value, max_parallel_executions: int = 1,
                 seeds: List[int] = None, specfiles: List[str] = None, expiration_timeouts=None,
                 output_persist:List[str] = None):
        if expiration_timeouts is None:
            expiration_timeouts = [consts.DEFAULT_EXPIRATION_TIMEOUT]
        self.expconf = expconf
        self.name = name
        self.strategies = strategies
        self.close_door_time = close_door_time
        self.stat_print_interval = stat_print_interval
        self.mab_update_interval = mab_update_interval
        self.mab_intermediate_sampling_update_interval = mab_intermediate_sampling_update_interval
        self.mab_intermediate_samples_keys = mab_intermediate_samples_keys
        self.axis_pre = axis_pre
        self.axis_post = axis_post
        self.iterable_params = iterable_params
        self.graphs = graphs
        self.rundup = rundup
        self.max_parallel_executions = max_parallel_executions
        self.seeds = [123] if seeds == None else seeds
        self.specfiles = specfiles
        self.expiration_timeouts = expiration_timeouts
        self.output_persist = output_persist

    def _generate_config(self, strategy: str, close_door_time: float, stat_print_interval: float, mab_update_interval: float, axis_pre: str, axis_post: str, param_names: List[str],
                         param_values: List[float], seed: int, specfile:str, mabinttime, mabintkeys, expiration_timeout:float):
        return write_custom_configfile(self.name, strategy, close_door_time, stat_print_interval, mab_update_interval, axis_pre, axis_post, param_names, param_values, seed,
                                       specfile, mabinttime, mabintkeys, expiration_timeout)

    # ritorna liste di dizionari del tipo [{par1: valore1, par2, valore2}, {par1: valore1, par2, valore2}, ...]
    # ove ciascun dizionario rappresenta i parametri di una singola istanza
    def enumerate_iterable_params(self, strategy:str)->List[dict]:
        ret=[]
        filtered_params = filter_strategy_params(self.iterable_params, strategy)
        ranges = [np.arange(param.start, param.end + param.step, param.step) for param in filtered_params]
        param_combinations_values=itertools.product(*ranges)
        names=[p.name for p in filtered_params]
        for values in param_combinations_values:
            dict={}
            for i,n in enumerate(names):
                value=values[i]
                recall=next(p for p in filtered_params if p.name==n)
                if value<=recall.end:
                    dict[n]=value
                    if len(dict)==len(filtered_params):
                        ret.append(dict)
        return ret

    def run(self):
        tmpfldr=os.path.abspath(os.path.join(os.path.dirname(__file__),consts.TEMP_FILES_DIR))

        if os.path.exists(tmpfldr):
            # TODO codice duplicato altrove
            shutil.rmtree(tmpfldr, ignore_errors=True)

        print(f"Starting experiment {self.name}...")

        # prepare output folder
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", self.name, consts.DEFAULT_OUTPUT_FOLDER))
        try:
            os.mkdir(output_dir)
        except OSError:
            pass

        # todo questo pezzo di codice è in API, vedere se/come unire
        max_procs = self.max_parallel_executions
        all_combinations = list(itertools.product(self.strategies, self.axis_pre, self.axis_post, self.seeds, self.specfiles, self.expiration_timeouts))

        in_list = []
        bayesopt=None

        for strat, axis_pre, axis_post, seed, specfile, expiration_timeout in all_combinations:
            if axis_post=="": axis_post=axis_pre
            bayesopt_value=None
            try:
                bayesopt_value = self.expconf["parameters"]["bayesopt"]
            except KeyError:
                bayesopt=False
                #bayesopt_value=False
            if bayesopt_value == "true": bayesopt=True
            elif bayesopt_value == "false": bayesopt=False

            param_combinations = None if bayesopt else self.enumerate_iterable_params(strat)
            for pc in param_combinations if param_combinations is not None else [None]:
                instance = MABExperimentInstanceRecord(strat, axis_pre, axis_post, pc, seed, None, specfile,
                                                       self.stat_print_interval, self.mab_update_interval,
                                                       self.mab_intermediate_sampling_update_interval,
                                                       self.mab_intermediate_samples_keys, expiration_timeout)

                in_list.append(instance)
        out_list = in_list if not bayesopt else bayesopt_search(in_list, max_procs, self.expconf)

        effective_procs = max(1, min(len(out_list), max_procs))
        cs=max(1,math.ceil(len(out_list)/effective_procs))
        with Pool(processes=effective_procs) as pool:
            pool.map(self._parall_run, out_list, chunksize=cs)

        tmpfldr=os.path.abspath(os.path.join(os.path.dirname(__file__),consts.TEMP_FILES_DIR))

        if os.path.exists(tmpfldr):
            # TODO codice duplicato altrove
            shutil.rmtree(tmpfldr, ignore_errors=True)

    def _parall_run(self, instance: MABExperimentInstanceRecord):
        rundup = logger.determine_simex_behavior(instance, self.rundup, self.output_persist)
        if rundup:
            params=instance.identifiers["parameters"]
            strategy=instance.identifiers["strategy"]
            ax_pre=instance.identifiers["axis_pre"]
            ax_post=instance.identifiers["axis_post"]
            seed=instance.identifiers["seed"]
            specfile = instance.identifiers["specfile"]
            expiration_timeout = instance.identifiers[EXPIRATION_TIMEOUT]
            print(f"Processing strategy={strategy}, ax_pre={ax_pre}, ax_post={ax_post}, seed={seed}, specfile={specfile}")
            print()
            print("============================================")
            print(f"Running experiment \"{self.name}\"")
            print(f"with the following configuration")
            # TODO instance.print_configuration
            print(f"\tStrategy:\t{strategy}")
            print(f"\tAxis:\t\t{ax_pre} -> {ax_post}")
            print(f"\tSeed:\t\t{seed}")
            print(f"\tParameters:")
            for k,v in params.items():
                print(f"\t\t> {k} = {v}")
            print(f"\tSpecfile:\t\t{specfile}")
            print(f"\tExpiration timeout:\t\t{expiration_timeout}")
            print("--------------------------------------------")
            param_names=[k for k,_ in params.items()]
            current_values=[v for _,v in params.items()]
            config_path = self._generate_config(strategy, self.close_door_time, self.stat_print_interval,
                                                self.mab_update_interval, ax_pre, ax_post, param_names, current_values,
                                                seed, specfile, self.mab_intermediate_sampling_update_interval, self.mab_intermediate_samples_keys,expiration_timeout)

            statsfile = generate_outfile_name(consts.PREFIX_STATSFILE, strategy, ax_pre, ax_post, param_names,
                current_values, seed, specfile, expiration_timeout) + consts.SUFFIX_STATSFILE

            mabfile = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_STATS_LOCATION,
                                                   consts.PREFIX_MABSTATSFILE + consts.SUFFIX_MABSTATSFILE + "-pid" + str(
                                                       os.getpid())))

            run_simulation=self.rundup
            if run_simulation:
                main(config_path)

            # processa l'output
            # (ev. nel post-processing)

            policies = []
            rewards = []

            dictt={k:[] for k in self.output_persist}


            def myprint(d):
                for k, v in d.items():
                    if isinstance(v, dict):
                        myprint(v)
                    if k in dictt.keys():
                        dictt[k].append(v)

            # extract the data requested to persist from all the output files
            for file in [statsfile, mabfile]:
                with open(file, 'r') as f:
                    data = json.load(f)
                    for d in data:
                        myprint(d)


                if self.output_persist.__contains__("cumavg-reward"):
                    for d in data:
                        policies.append(d["policy"])
                        rewards.append(d['reward'])
                    cumavg_reward = sum(rewards) / len(rewards)
                    dictt["cumavg-reward"]=cumavg_reward

            instance.add_experiment_result(dictt)
            logger.persist(instance, self.rundup)

            # TODO configurabili
            os.remove(config_path)
            os.remove(statsfile)
            os.remove(mabfile)

        print("Simulations completed.")
