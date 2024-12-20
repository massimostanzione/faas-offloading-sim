import json
import os
import sys
from abc import ABC
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _internal.consts import RewardFnAxis, WorkloadIdentifier

DEFAULT_LOGGER_PATH = "../_stats/log.json"


class MABExperimentInstanceRecord:
    def __init__(self,
                 strategy: str,
                 axis_pre: RewardFnAxis,
                 axis_post: RewardFnAxis,
                 params: List,
                 seed: int,
                 workload: WorkloadIdentifier
                 ):
        # instance identifiers
        self.identifiers={
            "strategy":strategy,
            "axis_pre":axis_pre,
            "axis_post":axis_post,
            "parameters":params,
            "seed":seed,
            "workload":workload,
        }

        # results from the experiments on this specific instance
        self.results = []


    def add_experiment_result(self, result):
        self.results.append(result)

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
        self.outfile_name = os.path.join(SCRIPT_DIR, outfile_name)#.__str__()

    def _compare_instances(self, inst1:MABExperimentInstanceRecord, inst2:MABExperimentInstanceRecord):
        print(inst1.identifiers)
        print(inst2.identifiers)

        return inst1.identifiers==inst2.identifiers

    def _update(self, found: MABExperimentInstanceRecord, results):
        # TODO handle duplicates
        found.add_experiment_result(results)
        return found

    def persist(self, instance: MABExperimentInstanceRecord):
        # super().persist()
        found=self.lookup(instance)
        if found is None:
            output = vars(inst)

            with open(self.outfile_name, 'r+') as file:
                file_data = json.load(file)
                file_data.append(output)
                file.seek(0)
                json.dump(file_data, file, indent=4)
        else:
            # instance already existent, we try to update instead of inserting
            updated=self._update(found, instance.results)
            output=vars(updated)

            with open(self.outfile_name, 'r+') as file:
                file_data = json.load(file)
                for d in file_data:
                    deser=_deserialize(d)
                    if self._compare_instances(inst, deser):
                        d["results"]=updated.results
                        break
                file.seek(0)
                json.dump(file_data, file, indent=4)


    def lookup(self, inst: MABExperimentInstanceRecord):
        # super().read()
        with open(self.outfile_name, "a+") as f:
            if os.path.getsize(self.outfile_name)==0:
                print("inizializzo il file")
                f.write("[]")
        with open(self.outfile_name, 'r+') as file:
            data = json.load(file)
            for d in data:
                deser=_deserialize(d)
                if self._compare_instances(inst, deser):
                    return deser
            return None

    def update(self):
        super().update()

    def remove(self):
        super().remove()

    # TODO strategy come oggetto/enum anziché str?

def _deserialize(dict):
    print("DESERIALIZING...")
    ret= MABExperimentInstanceRecord(
                                        dict["identifiers"]["strategy"],
                                        dict["identifiers"]["axis_pre"],
                                        dict["identifiers"]["axis_post"],
                                        dict["identifiers"]["parameters"],
                                        dict["identifiers"]["seed"],
                                        dict["identifiers"]["workload"],
                                       )
    ret.add_experiment_result(dict["results"])
    return ret

log = IncrementalLogger()
inst = MABExperimentInstanceRecord("None", None, None, None, None, None)
# s=json.dumps(inst.__dict__)
# print(s)
inst.add_experiment_result({"experiment1":["val1", "val2"]})
log.persist(inst)
