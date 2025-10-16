import itertools
import json
import os
from abc import ABC
from copy import deepcopy
from typing import List

from filelock import FileLock

import conf
from conf import EXPIRATION_TIMEOUT
from mab_automated_experiments._internal.reward_function_representation import RewardFunctionRepresentation, \
    RewardFunctionIdentifierConverter, RewardFnAxis

LOOKUP_OPTIMAL_HYPERPARAMETERS = -999
from mab_automated_experiments._internal.consts import WorkloadIdentifier, RundupBehavior, SUFFIX_LOCKFILE, \
    LOCK_FILE_PATH, PREFIX_LOCKFILE, STATS_FILES_DIR

DEFAULT_LOGGER_PATH = "../_stats/log-"


def custom_encoder(obj):
    if isinstance(obj, RewardFnAxis):
        return obj.value


class MABExperimentInstanceRecord:
    def __init__(self,
                 strategy: str,
                 reward_function: RewardFunctionRepresentation,
                 params: dict,
                 seed: int,
                 workload: WorkloadIdentifier,
                 specfile: str,
                 stat_print_interval: float,
                 mab_update_interval: float,
                 mab_intermediate_sampling_update_interval: float,
                 mab_intermediate_samples_keys: List[str],
                 mab_rtk_contextual_scenario: str,
                 expiration_timeout: float,
                 _call_from_factory: bool = False
                 ):

        if not _call_from_factory:
            raise RuntimeError("Please call this class via MABExperimentInstanceRecordFactory")

        self.reward_function = reward_function

        # instance identifiers
        identifiers_partial = {
            "strategy": strategy,
            "parameters": params,
            "seed": seed,
            "workload": workload,
            "specfile": specfile,
            conf.STAT_PRINT_INTERVAL: stat_print_interval,
            conf.MAB_UPDATE_INTERVAL: mab_update_interval,
            conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL: mab_intermediate_sampling_update_interval,
            conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS: mab_intermediate_samples_keys,
            conf.MAB_RTK_CONTEXTUAL_SCENARIOS: mab_rtk_contextual_scenario,
            EXPIRATION_TIMEOUT: expiration_timeout
        }
        self.identifiers = RewardFunctionIdentifierConverter.append_reward_function(self.reward_function,
                                                                                    identifiers_partial)

        # results from the experiments on this specific instance
        self.results = {}

    def to_log(self):
        return {attr: getattr(self, attr) for attr in ["identifiers", "results"]}

    def add_experiment_result(self, result: dict):
        for key, val in result.items():
            self.results[key] = val


class MABExperimentInstanceRecordFactory:

    @staticmethod
    def from_identifiers_dict(identifiers_dict: dict, optimal_hyperparams: dict = None) -> MABExperimentInstanceRecord:
        return MABExperimentInstanceRecord(
            identifiers_dict["strategy"],
            RewardFunctionIdentifierConverter.deserialize_reward_function(identifiers_dict),
            identifiers_dict["parameters"] if optimal_hyperparams is None else optimal_hyperparams,
            identifiers_dict["seed"],
            identifiers_dict["workload"],
            identifiers_dict["specfile"],
            identifiers_dict[conf.STAT_PRINT_INTERVAL] if conf.STAT_PRINT_INTERVAL in identifiers_dict else 360,
            identifiers_dict[conf.MAB_UPDATE_INTERVAL] if conf.MAB_UPDATE_INTERVAL in identifiers_dict else None,
            identifiers_dict[
                conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL] if conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL in identifiers_dict else None,
            identifiers_dict[
                conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS] if conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS in identifiers_dict else None,
            identifiers_dict[
                conf.MAB_RTK_CONTEXTUAL_SCENARIOS] if conf.MAB_RTK_CONTEXTUAL_SCENARIOS in identifiers_dict else None,
            identifiers_dict[EXPIRATION_TIMEOUT] if EXPIRATION_TIMEOUT in identifiers_dict else None,
            True
        )

    @staticmethod
    def from_experiment_objects(exp, extract_datarecords: bool = False) -> List[MABExperimentInstanceRecord]:

        logger = IncrementalLogger() if extract_datarecords else None
        records = []

        # if in the experiment config is required to execute bayesian optimization,
        # leave the hyperparameters data left blank: they will be filled later
        # by bayesian optimization
        is_bayesopt_required = None
        try:
            bayesopt_expconf_string = exp.expconf["parameters"]["bayesopt"]
            if bayesopt_expconf_string == "true":
                is_bayesopt_required = True
            elif bayesopt_expconf_string == "false":
                is_bayesopt_required = False
        except KeyError:
            is_bayesopt_required = False

        all_combinations = list(itertools.product(exp.strategies,
                                                  exp.reward_functions,
                                                  exp.seeds,
                                                  exp.specfiles,
                                                  exp.expiration_timeouts
                                                  )
                                )

        globalctr = 0
        target = 0
        for strategy, reward_function, seed, specfile, expiration_timeout in all_combinations:
            actual_rtk_scenarios = exp.mab_rtk_contextual_scenarios if "RTK-" in strategy else [""]
            for mab_rtk_contextual_scenario in actual_rtk_scenarios:
                hyperparam_combinations = None if is_bayesopt_required else exp.enumerate_iterable_hyperparams(strategy)
                for hpc in hyperparam_combinations if hyperparam_combinations is not None else [None]:
                    target += 1

        last_perc_print = -0.11
        for strategy, reward_function, seed, specfile, expiration_timeout in all_combinations:

            # [LEGACY] if the strategy is not RTK-contextual just leave the field blank
            # (for backward-compatibility with logged data previous to the introduction
            # of RTK-contextual strategies)
            actual_rtk_scenarios = exp.mab_rtk_contextual_scenarios if "RTK-" in strategy else [""]

            for mab_rtk_contextual_scenario in actual_rtk_scenarios:
                hyperparam_combinations = None if is_bayesopt_required else exp.enumerate_iterable_hyperparams(strategy)
                for hpc in hyperparam_combinations if hyperparam_combinations is not None else [None]:
                    instance_pre = MABExperimentInstanceRecord(strategy,
                                                               reward_function,
                                                               hpc,
                                                               seed,
                                                               None,  # legacy
                                                               specfile,
                                                               exp.stat_print_interval,
                                                               exp.mab_update_interval,
                                                               exp.mab_intermediate_sampling_update_interval,
                                                               exp.mab_intermediate_samples_keys,
                                                               mab_rtk_contextual_scenario,
                                                               expiration_timeout,
                                                               True
                                                               )

                    globalctr += 1
                    perc = globalctr / target
                    if perc - last_perc_print > 0.1 or abs(1 - (perc)) < 1e-2:
                        print(f"[logger] {int(perc * 100)}% done ({globalctr}/{target} instances processed)")
                        last_perc_print = perc
                    instance = logger.lookup(instance_pre) if extract_datarecords else instance_pre
                    records.append(instance)

        return records


class Logger(ABC):
    def read(self):
        pass

    def update(self):
        pass

    def remove(self):
        pass


class IncrementalLogger(Logger):

    def __init__(self, outfile_name: str = DEFAULT_LOGGER_PATH):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.outfile_name = os.path.abspath(
            os.path.join(os.path.dirname(__file__), LOCK_FILE_PATH, outfile_name))  # .__str__()

        statsfldr = os.path.abspath(os.path.join(os.path.dirname(__file__), STATS_FILES_DIR))
        try:
            os.mkdir(statsfldr)
        except OSError:
            pass

    # TODO sovrascrittura del metodo interno di python nativo
    def _compare_instances(self, inst1: MABExperimentInstanceRecord, inst2: MABExperimentInstanceRecord):
        return (inst1.identifiers) == (inst2.identifiers)

    def _update(self, found: MABExperimentInstanceRecord, results_new: dict):
        for new_res_key, new_res_value in results_new.items():
            if new_res_key not in found.results:
                found.add_experiment_result({new_res_key: new_res_value})
        return found

    def persist(self, instance: MABExperimentInstanceRecord, rundup: str = RundupBehavior.SKIP_EXISTENT.value):
        lockfilename = PREFIX_LOCKFILE + instance.identifiers["strategy"] + SUFFIX_LOCKFILE
        lockfilename_abs = os.path.abspath(os.path.join(os.path.dirname(__file__), LOCK_FILE_PATH, lockfilename))

        found = None if rundup == RundupBehavior.ALWAYS.value else self.lookup(instance)
        if found is None:
            output = instance.to_log()
            with FileLock(lockfilename):
                filename = self.outfile_name + instance.identifiers["strategy"] + ".json"
                if not os.path.isfile(filename): self._touch(filename)
                with open(filename, 'r+') as file:
                    file_data = json.load(file)
                    o = list(filter(lambda x: x['identifiers'] != (instance.identifiers), file_data))
                    o.append(output)
                    file.truncate(0)
                    file.seek(0)
                    json.dump(o, file, indent=4)
        else:
            # instance already existent, we try to update instead of inserting
            updated = self._update(found, instance.results)
            output = vars(updated)

            with FileLock(lockfilename):
                with open(self.outfile_name + instance.identifiers["strategy"] + ".json", 'r+') as file:
                    file_data = json.load(file)
                    for d in file_data:
                        deser = _deserialize(d)
                        if self._compare_instances(instance, deser):
                            d["results"] = updated.results
                            break
                    file.seek(0)
                    json.dump(file_data, file, default=custom_encoder, indent=4)
        try:
            os.remove(lockfilename_abs)
        except OSError:
            pass

    # output: le istanze che non sono già processate, i.e., quelle che dovranno essere eseguite (in parallelo, possibilmente)
    # OVVERO: prende oggetti di tipo instance e VA A CERCARE NEI LOG se i relativi log hanno gli specific_results
    # questa funzione manda in output SOLO LE FUNZIONI CHE *NON* HANNO I specific_results
    def filter_unprocessed_instances(self, list: List[MABExperimentInstanceRecord],
                                     specific_results: List[str] = None) -> List[MABExperimentInstanceRecord]:
        ret = []
        for instance in list:
            if specific_results is None:
                found = self.lookup(instance)
                if found is None:
                    ret.append(instance)
            else:
                found = self.lookup(instance, specific_results)
                if found is None:
                    ret.append(instance)
        return ret

    def lookup(self, inst: MABExperimentInstanceRecord, specific_results: List[str] = None):
        ret = None
        if inst.identifiers["parameters"] == LOOKUP_OPTIMAL_HYPERPARAMETERS:
            generic_inst = deepcopy(inst)
            generic_inst.identifiers["parameters"] = None
            inst.identifiers["parameters"] = self.lookup(generic_inst).results["optimal-params"]

        lockfilename = PREFIX_LOCKFILE + inst.identifiers["strategy"] + SUFFIX_LOCKFILE
        lockfilename_abs = os.path.abspath(os.path.join(os.path.dirname(__file__), LOCK_FILE_PATH, lockfilename))

        with FileLock(lockfilename):
            with open(self.outfile_name + inst.identifiers["strategy"] + ".json", "a+") as f:
                if os.path.getsize(self.outfile_name + inst.identifiers["strategy"] + ".json") == 0:
                    f.write("[]")
        try:
            os.remove(lockfilename_abs)
        except OSError:
            pass

        with FileLock(lockfilename):
            with open(self.outfile_name + inst.identifiers["strategy"] + ".json", 'r+') as file:
                data = json.load(file)
                for d in data:
                    deser = _deserialize(d)
                    if self._compare_instances(inst, deser):
                        if specific_results is None:
                            ret = deser
                        else:
                            ctr = 0
                            for key in deser.results.keys():
                                for specific_result in specific_results:
                                    if key == specific_result:
                                        ctr += 1
                                if ctr == len(specific_results):
                                    ret = deser
        try:
            os.remove(lockfilename_abs)
        except OSError:
            pass
        if ret is None: print(">>> non trovato per", inst.identifiers)
        return ret

    def determine_simex_behavior(self, instance: MABExperimentInstanceRecord, rundup, specific_results=None) -> bool:
        if rundup == RundupBehavior.ALWAYS.value:
            return True
        elif rundup == RundupBehavior.NO.value:
            return False
        elif rundup == RundupBehavior.SKIP_EXISTENT.value:
            return self.lookup(instance, specific_results) is None
        else:
            raise ValueError("invalid simex (\"run-duplicates\") value for", rundup,
                             ", please check your expconf.ini file")

    def _touch(self, filename):
        with open(filename, "w+") as f:
            json.dump([], f)
        f.close()


def _deserialize(dict):
    ret = MABExperimentInstanceRecordFactory.from_identifiers_dict(dict["identifiers"])
    ret.add_experiment_result(dict["results"])
    return ret
