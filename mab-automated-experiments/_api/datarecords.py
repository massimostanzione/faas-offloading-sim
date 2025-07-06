import itertools
import os
import sys
from typing import List

import conf
from conf import EXPIRATION_TIMEOUT

# TODO cambio nome packages per quanto segue
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _internal.logging import MABExperimentInstanceRecord, IncrementalLogger
from _internal.experiment import MABExperiment,  extract_iterable_params_from_config
from _internal.bayesopt import extract_optimal_parameters_for_instance
from _internal import consts

def extract_result_dict_from_datarecord(record:MABExperimentInstanceRecord, key:str)->dict:
    return record.results[key]

def extract_datarecords_from_exp_name(experiment_name:str)->List[MABExperimentInstanceRecord]:
    experiment_confpath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", experiment_name.strip(), consts.EXPCONF_FILE))
    return extract_datarecords_from_config_path(experiment_confpath)

def extract_datarecords_from_config_path(config_path:str)->List[MABExperimentInstanceRecord]:
    exp=None
    if os.path.exists(config_path):
        with open(config_path, "r") as expconf_file:
            config = conf.parse_config_file(config_path)
            axis_pre = config["reward_fn"]["axis_pre"].replace(' ', '').split(consts.DELIMITER_COMMA)
            axis_post = config["reward_fn"]["axis_post"].replace(' ', '').split(consts.DELIMITER_COMMA)
            is_single_axis = axis_post == ['']
            exp = MABExperiment(
                config,
                config["experiment"]["name"],
                config["strategies"]["strategies"].replace(' ', '').split(consts.DELIMITER_COMMA),
                config["experiment"]["close-door-time"],
                config["experiment"]["stat-print-interval"],
                config["experiment"]["mab-update-interval"],
                axis_pre,
                axis_post,# if not is_single_axis else axis_pre,
                extract_iterable_params_from_config(config),
                [],
                config["output"]["run-duplicates"],
                config.getint("experiment", "max-parallel-execution"),
                config["parameters"]["seeds"].replace(' ', '').split(consts.DELIMITER_COMMA),
                config["parameters"]["specfiles"].replace(' ', '').split(consts.DELIMITER_COMMA),
                config["parameters"][EXPIRATION_TIMEOUT].replace(' ', '').split(consts.DELIMITER_COMMA),
                config["output"]["persist"].replace(' ', '').split(consts.DELIMITER_COMMA)
            )
    else:
        raise RuntimeError("Path not found for", config_path)
    return extract_datarecords_from_experiment(exp)

def extract_datarecords_from_experiment(exp:MABExperiment)->List[MABExperimentInstanceRecord]:
    logger=IncrementalLogger()
    axis_post_upd=[''] if exp.axis_post==[''] else exp.axis_post
    all_combinations = list(itertools.product(exp.strategies, exp.axis_pre, axis_post_upd, exp.seeds, exp.specfiles))
    all_combinations = list(itertools.product(exp.strategies, exp.axis_pre, axis_post_upd, exp.seeds, exp.specfiles, exp.expiration_timeouts))

    in_list = []
    bayesopt = None


    for strat, axis_pre, axis_post, seed, specfile in all_combinations:
    for strat, axis_pre, axis_post, seed, specfile, expiration_timeout in all_combinations:
        if axis_post=='': axis_post=axis_pre
        print("APU", axis_post_upd, axis_pre, axis_post)
        # TODO bayesopt oppure parametri caricati exp.params
        # FIXME parametro workload
        bayesopt_value = None
        try:
            bayesopt_value = exp.expconf["parameters"]["bayesopt"]
        except KeyError:
            bayesopt = False
            # bayesopt_value=False
        if bayesopt_value == "true":
            bayesopt = True
        elif bayesopt_value == "false":
            bayesopt = False
        else:
            raise ValueError("\"bayesopt\" value misconfigured, please check your expconf.ini file")
        param_combinations = None if bayesopt else exp.enumerate_iterable_params(strat)
        for pc in param_combinations if param_combinations is not None else [None]:
            instance = MABExperimentInstanceRecord(strat, axis_pre, axis_post, pc, seed, None, specfile, exp.stat_print_interval, exp.mab_update_interval, expiration_timeout)
            if pc is None:
                instance.identifiers["parameters"]=extract_optimal_parameters_for_instance(instance)
            instance=logger.lookup(instance)
            in_list.append(instance)
    #out_list = in_list if not bayesopt else bayesopt_search(in_list, max_procs, exp.expconf)
    return in_list


# if the series we want to extract have a single value,
# i.e. "key" = "value"
def extract_timeseries_from_result_single(result_dict:List):
    output=[]
    for item in result_dict:
        output.append(item)
    return output

# if the series we want to extract is a sub-dictionary,
# i.e. "key" =  {
#               "cloud1": "value",
#               "cloud2": "value"
#               }
def extract_timeseries_from_result_multiple(result_dict:dict):
    output={k:[] for k in result_dict[0].keys()}
    for dict in result_dict:
        for k, v in dict.items():
            output[k].append(v)
    return output


def filter_datarecords_by_specfiles(results:List[MABExperimentInstanceRecord], requested_specfiles:List[str]=None) -> dict:
