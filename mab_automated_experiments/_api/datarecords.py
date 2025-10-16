import os
from typing import List

import os
from typing import List

import conf
from .expgen import build_experiment_from_config
from .._internal import consts
from .._internal.experiment import MABExperiment
from .._internal.logging import MABExperimentInstanceRecord, MABExperimentInstanceRecordFactory


def extract_probed_contextinfo_data_from_datarecord(record: MABExperimentInstanceRecord, key: str) -> List:
    output = []
    context_info_timeseries = extract_result_dict_from_datarecord(record, "context_info")
    probed_data_timeseries = []
    for item in context_info_timeseries:
        probed_data_timeseries.append(item["probed_data"])
    for probed_data_point in probed_data_timeseries:
        for k, v in probed_data_point.items():
            if k == key:
                output.append(v)
    return output

def extract_result_dict_from_datarecord(record: MABExperimentInstanceRecord, key: str) -> dict:
    return record.results[key]


def extract_datarecords_from_exp_name(experiment_name: str) -> List[MABExperimentInstanceRecord]:
    print(f"Extracting data records for experiment {experiment_name}. It might take a while, please wait...")
    experiment_confpath = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", experiment_name.strip(), consts.EXPCONF_FILE))
    return extract_datarecords_from_config_path(experiment_confpath)


def extract_datarecords_from_config_path(config_path: str) -> List[MABExperimentInstanceRecord]:
    exp = None
    if os.path.exists(config_path):
            config = conf.parse_config_file(config_path)
            exp = build_experiment_from_config(config)
    else:
        raise RuntimeError("Path not found for", config_path)
    return extract_datarecords_from_experiment(exp)


def extract_datarecords_from_experiment(exp: MABExperiment) -> List[MABExperimentInstanceRecord]:
    return MABExperimentInstanceRecordFactory.from_experiment_objects(exp, True)


# if the series we want to extract have a single value,
# i.e. "key" = "value"
def extract_timeseries_from_result_single(result_dict: List):
    output = []
    for item in result_dict:
        output.append(item)
    return output


# if the series we want to extract is a sub-dictionary,
# i.e. "key" =  {
#               "cloud1": "value",
#               "cloud2": "value"
#               }
def extract_timeseries_from_result_multiple(result_dict: dict):
    output = {k: [] for k in result_dict[0].keys()}
    for dict in result_dict:
        for k, v in dict.items():
            output[k].append(v)
    return output


def filter_datarecords_by_specfiles(results: List[MABExperimentInstanceRecord],
                                    requested_specfiles: List[str] = None) -> dict:
    # if not specified, gather them from the result list
    if requested_specfiles is None:
        # gather the specfiles
        requested_specfiles = []
        for r in results:
            if r.identifiers["specfile"] not in requested_specfiles:
                requested_specfiles.append(r.identifiers["specfile"])

    # filter based on requested specfiles
    filtered = {specfile: [] for specfile in requested_specfiles}
    for r in results:
        if r.identifiers["specfile"] in requested_specfiles:
            filtered[r.identifiers["specfile"]].append(r)

    return filtered
