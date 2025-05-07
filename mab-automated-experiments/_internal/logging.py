import json
import os
import sys
from abc import ABC
from copy import deepcopy
from typing import List

from filelock import FileLock
LOOKUP_OPTIMAL_PARAMETERS=-999
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _internal.consts import RewardFnAxis, WorkloadIdentifier, RundupBehavior, SUFFIX_LOCKFILE, LOCK_FILE_PATH, PREFIX_LOCKFILE, STATS_FILES_DIR

DEFAULT_LOGGER_PATH = "../_stats/log-"

class MABExperimentInstanceRecord:
    def __init__(self,
                 strategy: str,
                 axis_pre: RewardFnAxis,
                 axis_post: RewardFnAxis,
                 params: dict,
                 seed: int,
                 workload: WorkloadIdentifier,
                 specfile: str,
                 mab_update_interval: float
                 ):
        # instance identifiers
        self.identifiers={
            "strategy":strategy,
            "axis_pre":axis_pre,
            "axis_post":axis_post,
            "parameters":params,
            "seed":seed,
            "workload":workload,
            "specfile":specfile,
            "mab-update-interval":mab_update_interval
        }

        # results from the experiments on this specific instance
        self.results = {}


    def add_experiment_result(self, result:dict):
        for key, val in result.items():
            self.results[key]=val

class Logger(ABC):
    # def persist(self):
    #    pass

    def read(self):
        pass

    def update(self):
        pass

    def remove(self):
        pass


class IncrementalLogger(Logger):

    def __init__(self, outfile_name: str = DEFAULT_LOGGER_PATH):
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.outfile_name = os.path.abspath(os.path.join(os.path.dirname(__file__),LOCK_FILE_PATH,outfile_name))#.__str__()

        statsfldr=os.path.abspath(os.path.join(os.path.dirname(__file__), STATS_FILES_DIR))
        try:
            os.mkdir(statsfldr)
        except OSError:
            pass

    def _compare_instances(self, inst1:MABExperimentInstanceRecord, inst2:MABExperimentInstanceRecord):
        return inst1.identifiers==inst2.identifiers

    def _update(self, found: MABExperimentInstanceRecord, results_new:dict):
        for new_res_key, new_res_value in results_new.items():
            if new_res_key not in found.results:
                found.add_experiment_result({new_res_key:new_res_value})
                # (persistence is done afterwards into the caller function, not here)
            #else:
                #found.results[new_res_key]=new_res_value
        return found

    def persist(self, instance: MABExperimentInstanceRecord, rundup: str=RundupBehavior.SKIP_EXISTENT.value):
        # super().persist()
        lockfilename = PREFIX_LOCKFILE + instance.identifiers["strategy"] + SUFFIX_LOCKFILE
        lockfilename_abs = os.path.abspath(os.path.join(os.path.dirname(__file__), LOCK_FILE_PATH, lockfilename))

        found = None if rundup==RundupBehavior.ALWAYS.value else self.lookup(instance)
        if found is None:
            output = vars(instance)
            with FileLock(lockfilename):
                with open(self.outfile_name+instance.identifiers["strategy"]+".json", 'r+') as file:
                    file_data = json.load(file)
                    o = list(filter(lambda x: x['identifiers'] != (instance.identifiers), file_data))
                    print(o)
                    o.append(output)
                    file.truncate(0)
                    file.seek(0)
                    json.dump(o, file, indent=4)
        else:
            # instance already existent, we try to update instead of inserting
            updated=self._update(found, instance.results)
            output=vars(updated)

            with FileLock(lockfilename):
                with open(self.outfile_name+instance.identifiers["strategy"]+".json", 'r+') as file:
                    file_data = json.load(file)
                    for d in file_data:
                        deser=_deserialize(d)
                        if self._compare_instances(instance, deser):
                            d["results"]=updated.results
                            break
                    file.seek(0)
                    json.dump(file_data, file, indent=4)
        try:
            os.remove(lockfilename_abs)
        except OSError:
            pass

    # output: le istanze che non sono già processate, i.e., quelle che dovranno essere eseguite (in parallelo, possibilmente)
    def filter_unprocessed_instances(self, list:List[MABExperimentInstanceRecord], specific_results:List[str]=None)->List[MABExperimentInstanceRecord]:
        ret=[]
        for instance in list:
            if specific_results is None:
                found=self.lookup(instance)
                print(found)
                if found is None:
                    ret.append(instance)
            else:
                for specific_result in specific_results:
                    found=self.lookup(instance, specific_results)
                    print(found)
                    if found is None:
                        ret.append(instance)
        return ret

    def lookup(self, inst: MABExperimentInstanceRecord, specific_results:List[str]=None):
        ret=None

        if inst.identifiers["parameters"]==LOOKUP_OPTIMAL_PARAMETERS:
            generic_inst=deepcopy(inst)
            generic_inst.identifiers["parameters"]=None
            inst.identifiers["parameters"]=self.lookup(generic_inst).results["optimal-params"]

        lockfilename=PREFIX_LOCKFILE+inst.identifiers["strategy"]+SUFFIX_LOCKFILE
        lockfilename_abs=os.path.abspath(os.path.join(os.path.dirname(__file__),LOCK_FILE_PATH,lockfilename))

        with FileLock(lockfilename):
            with open(self.outfile_name+inst.identifiers["strategy"]+".json", "a+") as f:
                if os.path.getsize(self.outfile_name+inst.identifiers["strategy"]+".json")==0:
                    print("inizializzo il file")
                    f.write("[]")
        try:
            os.remove(lockfilename_abs)
        except OSError:
            pass

        with FileLock(lockfilename):
            with open(self.outfile_name+inst.identifiers["strategy"]+".json", 'r+') as file:
                data = json.load(file)
                for d in data:
                    deser=_deserialize(d)
                    if self._compare_instances(inst, deser):
                        if specific_results is None:
                            ret= deser
                        else:
                            ctr=0
                            #for dict in deser.results:
                            for key in deser.results.keys():
                                for specific_result in specific_results:
                                    #print(specific_result)
                                    if key==specific_result:
                                        ctr+=1
                                        print("MATCH", key, ctr)
                                        #continue
                                if ctr==len(specific_results):
                                    ret= deser
        try:
            os.remove(lockfilename_abs)
        except OSError:
            pass
        return ret

    def determine_simex_behavior(self, instance:MABExperimentInstanceRecord, rundup, specific_results=None) -> bool:
        if rundup == RundupBehavior.ALWAYS.value:
            return True
        elif rundup == RundupBehavior.NO.value:
            return False
        elif rundup == RundupBehavior.SKIP_EXISTENT.value:
            return self.lookup(instance, specific_results) is None

def _deserialize(dict):
    ret= MABExperimentInstanceRecord(
                                        dict["identifiers"]["strategy"],
                                        dict["identifiers"]["axis_pre"],
                                        dict["identifiers"]["axis_post"],
                                        dict["identifiers"]["parameters"],
                                        dict["identifiers"]["seed"],
                                        dict["identifiers"]["workload"],
                                        dict["identifiers"]["specfile"],
                                        dict["identifiers"]["mab-update-interval"],
                                       )
    ret.add_experiment_result(dict["results"])
    return ret