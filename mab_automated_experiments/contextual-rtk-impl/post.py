import os
import sys
from datetime import datetime

from matplotlib import pyplot as plt
from numpy import arange

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from mab_automated_experiments._api.datarecords import extract_datarecords_from_exp_name, extract_result_dict_from_datarecord
from mab_automated_experiments._internal import consts, utils
records=extract_datarecords_from_exp_name("contextual-rtk-impl")

timestamp = datetime.now().replace(microsecond=0)
graphs_ctr=1
trace_iat=[]
tempi_transizioni=[]
valori_plot=[]
mem=[]
instances=[]
for r in records:
    print("RECORD", r.identifiers["axis_post"])
    tracename=r.identifiers["specfile"]
    if "specbase" in tracename:
        tempi_transizioni=[0,0,0]
        valori_plot=[0,0,0]
    else:
        path=os.path.abspath("_traces/"+tracename+"_rates.iat")
        if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        tempi_transizioni.append(float(line))
        path=os.path.abspath("_traces/"+tracename+"_rates.iat")
        if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        valori_plot.append(float(line))

    mem = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys")
    instances = extract_result_dict_from_datarecord(r, "instance_invoked")
    time = extract_result_dict_from_datarecord(r, "time")
    policies = extract_result_dict_from_datarecord(r, "policy")
    trace_rates=[]
    trace_ratesa=[]
    if len(time)>len(tempi_transizioni):
        pass
    if len(time)<len(tempi_transizioni):
        step=int(len(tempi_transizioni) / len(time))
        print(len(time), len(tempi_transizioni), step)
        for i in arange(0, len(tempi_transizioni), step):
            trace_ratesa.append(tempi_transizioni[i])
            trace_rates=trace_ratesa[1:]
    else:
        trace_rates=tempi_transizioni
    x=mem

    z=mem
    labels=instances
    valori=mem
    dati_per_label = {}
    for label in set(labels):
        dati_per_label[label] = {"x": [], "y": [], "c": [], "o_x": [], "o_y": [], "o_c": []}

    policy_colors = utils.get_policy_colors()

    for i, label in enumerate(labels):
        policy = policies[i]
        policy_colore = policy_colors[policy]
        if len(dati_per_label[label]["y"]) < 7:
            dati_per_label[label]["x"].append(time[i])
            dati_per_label[label]["y"].append(valori[i])
            dati_per_label[label]["c"].append(policy_colore)
        else:
            dati_per_label[label]["o_x"].append(time[i])
            dati_per_label[label]["o_y"].append(valori[i])
            dati_per_label[label]["o_c"].append(policy_colore)

    fig, ax1 = plt.subplots()

    plt.hlines(y=0.333, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={3}$")
    plt.hlines(y=0.666, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={6}$")
    plt.hlines(y=1, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={1}$")

    color = 'tab:red'
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('exp', color=color)
    ax1.set_ylim([0,1])
    for label, data in dati_per_label.items():
        ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
        ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()

    color = 'tab:blue'
    ax2.set_ylabel('sin', color=color)
    ax2.plot(valori_plot, color=color, drawstyle='steps-post')
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()

    plt.title(r.identifiers["axis_pre"]+" "+r.identifiers["strategy"]+" "+r.identifiers["specfile"]+" "+tracename)



    graphs_ctr += 1
    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + ".svg"))
    fig.clf()




