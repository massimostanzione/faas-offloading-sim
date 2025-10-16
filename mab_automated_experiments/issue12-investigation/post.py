from conf import EXPIRATION_TIMEOUT
from issue12_plots import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from mab_automated_experiments._api.datarecords import (extract_datarecords_from_exp_name, extract_result_dict_from_datarecord,
                              extract_timeseries_from_result_single, extract_timeseries_from_result_multiple,
                              filter_datarecords_by_specfiles
                              )
records = extract_datarecords_from_exp_name("issue12-investigation")

graphs_ctr = 0
curr_specfile = ""

filtered_records = filter_datarecords_by_specfiles(records)
for specfile in list(filtered_records.keys()):
    curr_specfile = specfile
    print("> plotting for", specfile)
    series_avgMemUtil = {}
    series_avgMemUtilUO = {}
    series_warmContainers = {}
    series_availMem = {}
    series_coldStartProb = {}
    series_drops = {}
    series_srate = {}
    for r in filtered_records[specfile]:
        time = extract_result_dict_from_datarecord(r, "time")
        et = r.identifiers[EXPIRATION_TIMEOUT]
        mem = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys")
        memUO = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys")
        warm_ctr = extract_result_dict_from_datarecord(r, "warm_ctr")
        avMem = extract_result_dict_from_datarecord(r, "availableMemory_sys")
        coldStartProb = extract_result_dict_from_datarecord(r, "coldStartProb")
        drops = extract_result_dict_from_datarecord(r, "drops_sys")
        srate = extract_result_dict_from_datarecord(r, "sampledRate")
        series_avgMemUtil[et] = extract_timeseries_from_result_single(mem)
        series_avgMemUtilUO[et] = extract_timeseries_from_result_single(memUO)
        series_warmContainers[et] = (extract_timeseries_from_result_multiple(warm_ctr))
        series_availMem[et] = extract_timeseries_from_result_single(avMem)
        series_coldStartProb[et] = extract_timeseries_from_result_multiple(coldStartProb)
        series_drops[et] = extract_timeseries_from_result_single(drops)
        series_srate[et] = extract_timeseries_from_result_single(srate)
    r = records[0]
    time = extract_result_dict_from_datarecord(r, "time")

    refined = {k: [0] * len(time) for k, _ in series_warmContainers.items()}
    for EF, ef_dict_cloud_series in series_warmContainers.items():
        for cloud_label, timeseries_list in ef_dict_cloud_series.items():
            for i in range(len(timeseries_list)):
                refined[EF][i] += timeseries_list[i]

    refined_CS = {k: [0] * len(time) for k, _ in series_coldStartProb.items()}
    for EF, ef_dict_cloud_series in series_coldStartProb.items():
        for cloud_label, timeseries_list in ef_dict_cloud_series.items():
            for i in range(len(timeseries_list)):
                refined_CS[EF][i] += timeseries_list[i]
        refined_CS[EF] = [k / 8 for k in refined_CS[EF]]

    graph_avgMemUtil(series_avgMemUtil, time, curr_specfile, ["600"])
    graph_avgMemUtil(series_avgMemUtilUO, time, curr_specfile, ["600"], True)
    graph_warmContainers(refined, time, curr_specfile, ["600"])
    graph_availMem(series_availMem, time, curr_specfile, ["600"])
    graph_coldStartProb(refined_CS, time, curr_specfile, ["600"])
    graph_drops(series_drops, time, curr_specfile, ["600"])
    graphs_ctr += 1
