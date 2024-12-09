import json
import os
import sys
from datetime import datetime
from json import JSONDecodeError
from multiprocessing import Pool
from pathlib import Path

import conf
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from _internal import consts
from _internal.experiment import generate_outfile_name
from _internal.experiment import write_custom_configfile
from main import main
to_be_executed=[]
EXPNAME = "policies-choices"
EXPCONF_PATH = os.path.join(EXPNAME, consts.EXPCONF_FILE)

def _parall_run(params):
    print(">",params)
    for d in params:
        params = d["parameters"]
        strat = d["strategy"]
        ax_pre = d["axis_pre"]
        ax_post = d["axis_post"]
        #configname = EXPNAME + "/results/" + consts.CONFIG_FILE + "-pid" + str(os.getpid())
        configname=write_custom_configfile(EXPNAME, strat, ax_pre, ax_post, list(params.keys()), list(params.values()))
        main(configname)
        os.remove(configname)


def mainn():
    timestamp = datetime.now().replace(microsecond=0)
    config = conf.parse_config_file(EXPCONF_PATH)

    paramfilecfg = config["parameters"]["optimized-params-file"]
    rundup = config["output"]["run-duplicates"]
    paramfile = os.path.abspath(os.path.join(os.path.dirname(__file__), paramfilecfg))

    max_parallel_executions = config.getint("experiment", "max-parallel-execution")

    strategies = config["strategies"]["strategies"].split(consts.DELIMITER_COMMA)

    axis_pre = config["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
    axis_post = config["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)


    graphs_ctr = -1

    with open(paramfile, 'r') as f:
        data = json.load(f)
        for d in data:
            #for strat in strategies:
                #for ax_pre in axis_pre:
                    #for ax_post in axis_post:
                        params=d["parameters"]

                        strat=d["strategy"]
                        ax_pre=d["axis_pre"]
                        ax_post=d["axis_post"]
                        print(strat, params, list(params.keys()), list(params.values()))


                        statsfile = generate_outfile_name(
                            consts.PREFIX_STATSFILE, strat, ax_pre, ax_post,
                            list(params.keys()),list(params.values())
                        ) + consts.SUFFIX_STATSFILE
                        mabfile = generate_outfile_name(
                            consts.PREFIX_MABSTATSFILE, strat, ax_pre, ax_post,
                            list(params.keys()),
                            list(params.values())
                        ) + consts.SUFFIX_MABSTATSFILE
                        print(rundup, mabfile)
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
                            to_be_executed.append(d)





                        a=d["strategy"]
                        path=write_custom_configfile
                        #if a== strat: print(d)
    chunk_size = len(to_be_executed) // max_parallel_executions
    remainder = len(to_be_executed) % max_parallel_executions
    chunks = []
    start = 0
    for i in range(max_parallel_executions):
        end = start + chunk_size + (1 if i < remainder else 0)
        chunks.append(to_be_executed[start:end])
        start = end
    #return chunks
    with Pool(processes=max_parallel_executions) as pool:
        pool.map(_parall_run, chunks)
    print("sims terminated")

if __name__ == "__main__":
    mainn()
