import os
import sys
from datetime import datetime

from matplotlib import pyplot as plt
from numpy import arange
import numpy as np
from scipy.interpolate import interp1d

print(os.getcwd())
print(sys.path)
exit(0)
import conf
from mab.contextual.utils import is_strategy_RTK

from mab_automated_experiments._api.datarecords import (extract_datarecords_from_exp_name,
                                                        extract_result_dict_from_datarecord,
                                                        extract_timeseries_from_result_single,
                                                        extract_timeseries_from_result_multiple,
                                                        filter_datarecords_by_specfiles,
                                                        extract_probed_contextinfo_data_from_datarecord
                                                        )
from mab_automated_experiments._internal import consts, utils
from mab_automated_experiments._internal.consts import DELIMITER_COMMA, METASIM_DIR
expname = "sep25_e11_group1"
records = extract_datarecords_from_exp_name(expname)
print(len(records))
timestamp = datetime.now().replace(microsecond=0)
graphs_ctr = 0
trace_iat = []
tempi_transizioni = []
valori_plot = []
mem = []
instances = []

print(len(records))
timestamp = datetime.now().replace(microsecond=0)
graphs_ctr = 0
trace_iat = []
tempi_transizioni = []
valori_plot = []
mem = []
instances = []

print(len(records))
timestamp = datetime.now().replace(microsecond=0)
graphs_ctr = 0
trace_iat = []
tempi_transizioni = []
valori_plot = []
mem = []
instances = []
SCRIPT_DIR = os.path.join(os.getcwd(), METASIM_DIR, expname)
with open(os.path.join(SCRIPT_DIR, "output", "rewards.txt"), "w+") as rewfile:
    for r in records:
        rewfile.write(
            r.identifiers["specfile"] + "\t" +
            r.identifiers["strategy"] + "\t" +
            r.identifiers["axis_pre"] + "\t" +
            r.identifiers["mab-rtk-contextual-scenarios"] + "\t" +
            str(r.identifiers["parameters"]) + "\t" +
            str(r.results["cumavg-reward"]) + "\t" +
            "\n")

specfiles = set([r.identifiers["specfile"] for r in records])
axis = set([r.identifiers["axis_pre"] for r in records])
strategies = set([r.identifiers["strategy"] for r in records])
scenarios = set([r.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS] for r in records])


for specfile in specfiles:
    for ax in axis:
        with open(os.path.join(SCRIPT_DIR, "output", "params-" + specfile + "-" + ax + ".csv"), "w+") as paramfile:
            paramfile.write("strategy,scenario,ef,alpha,c\n")
            for r in records:
                for s in strategies:
                    for sc in scenarios:
                        if (
                                r.identifiers["specfile"] == specfile and
                                r.identifiers["axis_pre"] == ax and
                                r.identifiers["strategy"] == s and
                                r.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS] == sc
                        ):
                            row = s + DELIMITER_COMMA + sc + DELIMITER_COMMA
                            pdict = r.identifiers["parameters"]
                            row += (str(pdict["ef"]) if "ef" in pdict else "N/A") + DELIMITER_COMMA + \
                                   (str(pdict["alpha"]) if "alpha" in pdict else "N/A") + DELIMITER_COMMA + \
                                   (str(pdict["c"]) if "c" in pdict else "N/A")
                            paramfile.write(
                                row +
                                "\n")
for specfile in specfiles:
    for ax in axis:
        with open(os.path.join(SCRIPT_DIR, "output", "rewards-compared-" + specfile + "-" + ax + ".csv"),
                  "w+") as paramfile:
            paramfile.write("strategy, scenario, reward\n")
            for r in records:
                for s in strategies:
                    for sc in scenarios:
                        if (
                                r.identifiers["specfile"] == specfile and
                                r.identifiers["axis_pre"] == ax and
                                r.identifiers["strategy"] == s and
                                r.identifiers[conf.MAB_RTK_CONTEXTUAL_SCENARIOS] == sc
                        ):
                            row = s + DELIMITER_COMMA + sc + DELIMITER_COMMA
                            row += str(r.results["cumavg-reward"])
                            paramfile.write(
                                row +
                                "\n")
for r in records:
    trace_iat = []
    tempi_transizioni = []
    valori_plot = []
    mem = []
    instances = []
    path = ""
    print("RECORD", r.identifiers["axis_post"])
    tracename = r.identifiers["specfile"]
    if tracename == "sfasate_sinusoid": tracename = "sinus_delay0"
    if tracename == "sfasate_bell": tracename = "bell_delay0"
    if "specbase" in tracename:
        tempi_transizioni = [0, 0, 0]
        valori_plot = [0, 0, 0]
    else:
        print("UUUUUUUUUUU")
        path = os.path.abspath("_traces/" + tracename
                               .replace("_f1", "")
                               .replace("_f2", "")
                               .replace("_f3", "")
                               .replace("_f4", "")
                               .replace("_f5", "")
                               .replace("_x5", "")
                               .replace("_full", "")
                               + "_rates.iat")
        print(path)
        if os.path.exists(path):
            with open(path) as file:
                line_old = 0
                for line in file:
                    if line != "Rate\n":
                        tempi_transizioni.append(float(line))
        
    print(r.identifiers["strategy"], is_strategy_RTK(r.identifiers["strategy"]))
    if is_strategy_RTK(r.identifiers["strategy"]):
        mem = extract_probed_contextinfo_data_from_datarecord(r, "activeMemoryUtilization_sys")
        instances = extract_result_dict_from_datarecord(r, "instance_invoked")
    else:
        mem = extract_result_dict_from_datarecord(r, "activeMemoryUtilization_sys")
        instances = ["uno"] * (len(mem))
    time = extract_result_dict_from_datarecord(r, "time")
    policies = extract_result_dict_from_datarecord(r, "policy")
    rewards = extract_result_dict_from_datarecord(r, "reward")
    ctx_epochstart_series = extract_result_dict_from_datarecord(r, "epochStartTimes_ctx")
    scenario_action_serie = extract_result_dict_from_datarecord(r, "scenario_action")
    trace_rates = []
    trace_ratesa = []
    if len(time) > len(tempi_transizioni):
        pass
    if len(time) < len(tempi_transizioni):
        step = int(len(tempi_transizioni) / len(time))
        print(len(time), len(tempi_transizioni), step)
        for i in arange(0, len(tempi_transizioni), step):
            trace_ratesa.append(tempi_transizioni[i])
            trace_rates = trace_ratesa[1:]
    else:
        trace_rates = tempi_transizioni
    x = mem

    z = mem
    labels = instances
    valori = mem
    dati_per_label = {}
    for label in set(labels):
        dati_per_label[label] = {"x": [], "y": [], "c": [], "o_x": [], "o_y": [], "o_c": []}

    policy_colors = utils.get_policy_colors()
    print("x", len(valori), len(labels))
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
    
    xmin = 0
    xmax = time[len(time) - 1]

    

    fig, (ax1, ax_destro) = plt.subplots(1, 2, figsize=(12, 6))

    ax1.set_title("Utilizzo memoria e policy scelte")

    ax1.hlines(y=0.333, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1,
               label="limiti istanze")
    ax1.hlines(y=0.666, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1)
    ax1.hlines(y=1, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1)

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization', color=color)
    ax1.set_ylim([0, 1])
    for label, data in dati_per_label.items():
        ax1.scatter(data["x"], data["y"], marker='x', c=data["c"])
        ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"])
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()

    color = 'tab:blue'
    ax2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)

    tempi_n1 = np.array(time)
    tempi_destinazione = []
    dati_n2_resampled = []
    print("TRACENAME", tracename)


    def converti_traccia(tempi_n1):
        tempi_n2_impliciti = np.linspace(tempi_n1.min(), tempi_n1.max(),
                                         len(tempi_transizioni))
        tempi_destinazione = np.linspace(tempi_n1.min(), tempi_n1.max(), len(tempi_n1))
        funzione_interpolazione = interp1d(tempi_n2_impliciti, tempi_transizioni, kind='linear',
                                           fill_value="extrapolate")
        dati_n2_resampled = funzione_interpolazione(tempi_destinazione)
        return tempi_destinazione, dati_n2_resampled


    if True:
        if os.path.exists(path):
            tempi_n2_impliciti = np.linspace(tempi_n1.min(), tempi_n1.max(),
                                             len(tempi_transizioni))
            tempi_destinazione = np.linspace(tempi_n1.min(), tempi_n1.max(), len(tempi_n1))
            funzione_interpolazione = interp1d(tempi_n2_impliciti, tempi_transizioni, kind='linear',
                                               fill_value="extrapolate")
            dati_n2_resampled = funzione_interpolazione(tempi_destinazione)

            ax2.plot(tempi_destinazione, dati_n2_resampled, drawstyle='steps-post', linestyle='--', linewidth=0.7)
            ax2.tick_params(axis='y', labelcolor=color)
            ax_destro.plot(tempi_destinazione, dati_n2_resampled, drawstyle='steps-post', linestyle='--', linewidth=0.7)
            ax_destro.tick_params(axis='y', labelcolor=color)

    else:
        print("NOOOOOO")
        for i in range(5):

            path2 = path[:-11]
            path2 = path2 + str(i) + "_rates.iat"
            print(">>>>>", path2)
            if os.path.exists(path2):
                with open(path2) as file:
                    line_old = 0
                    for line in file:
                        if line != "Rate\n":
                            tempi_transizioni.append(float(line))
            
            trace_rates = []
            trace_ratesa = []
            if len(time) > len(tempi_transizioni):
                pass
            if len(time) < len(tempi_transizioni):
                step = int(len(tempi_transizioni) / len(time))
                print(len(time), len(tempi_transizioni), step)
                for i in arange(0, len(tempi_transizioni), step):
                    trace_ratesa.append(tempi_transizioni[i])
                    trace_rates = trace_ratesa[1:]
            else:
                trace_rates = tempi_transizioni
                tempi_n2_impliciti = np.linspace(tempi_n1.min(), tempi_n1.max(),
                                                 len(tempi_transizioni))
                tempi_destinazione = np.linspace(tempi_n1.min(), tempi_n1.max(), len(tempi_n1))
                funzione_interpolazione = interp1d(tempi_n2_impliciti, tempi_transizioni, kind='linear',
                                                   fill_value="extrapolate")
                dati_n2_resampled = funzione_interpolazione(tempi_destinazione)

                ax2.plot(tempi_destinazione, dati_n2_resampled, drawstyle='steps-post', linestyle='--', linewidth=0.7)
                ax2.tick_params(axis='y', labelcolor=color)
                ax_destro.plot(tempi_destinazione, dati_n2_resampled, drawstyle='steps-post', linestyle='--',
                               linewidth=0.7)
                ax_destro.tick_params(axis='y', labelcolor=color)

    
    label_precedente = None
    for i in range(len(instances)):
        label_corrente = instances[i]
        if i > 0 and label_corrente != label_precedente:
            ax1.axvline(x=time[i], color='gray', linestyle='--', linewidth=0.7)
            ax_destro.axvline(x=time[i], color='gray', linestyle='--', linewidth=0.7)
        label_precedente = label_corrente

    linee_verticali_config = []
    for item in ctx_epochstart_series:
        for key, time_value in item.items():
            parts = key.split('-')
            try:
                ymin_str = parts[-2]
                ymax_str = parts[-1]
                ymin_val = float(ymin_str)
                ymax_val = float(ymax_str)
                linee_verticali_config.append({"time": time_value, "ymin": ymin_val, "ymax": ymax_val})
            except (IndexError, ValueError) as e:
                print(
                    f"Errore durante l'estrazione di ymin/ymax dalla chiave '{key}': {e}. Salto questa configurazione.")
                continue

    for line_data in linee_verticali_config:
        t = line_data["time"]
        ymin_val = line_data["ymin"]
        ymax_val = line_data["ymax"]
        ax1.axvline(x=t, ymin=ymin_val, ymax=ymax_val, color='orange', linestyle='--', linewidth=1.5)
        ax_destro.axvline(x=t, ymin=ymin_val, ymax=ymax_val, color='orange', linestyle='--', linewidth=1.5)

    scenario_action = []
    for t in scenario_action_serie:
        ax1.axvline(x=t, ymin=0, ymax=1, color='black', linestyle='-', linewidth=1.5)
        ax_destro.axvline(x=t, ymin=0, ymax=1, color='orange', linestyle='-', linewidth=1.5)

    if linee_verticali_config:
        ax1.plot([], [], color='orange', linestyle='--', linewidth=1.5, label='Inizio epoca')
        ax1.legend()
    ax_destro.plot(time, rewards, marker='o', linestyle='-', color='green', label='Reward')
    ax_destro.set_xlabel('Tempo [s]')
    ax_destro.set_ylabel('Reward (puntuale)', color='green')
    ax_destro.tick_params(axis='y', labelcolor='green')
    ax_destro.set_title('Reward (puntuale)')
    min_rewards = np.min(rewards)
    max_rewards = np.max(rewards)
    ax_destro.set_ylim(min_rewards, max_rewards)

    if os.path.exists(path):
        ax_destro_y2 = ax_destro.twinx()
        color = 'tab:blue'
        ax_destro_y2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)
        ax_destro_y2.plot(tempi_destinazione, dati_n2_resampled, color=color, drawstyle='steps-post', linestyle='--',
                          linewidth=0.7, label='Traccia')
        ax_destro_y2.tick_params(axis='y', labelcolor=color)
        min_y2 = np.min(dati_n2_resampled)
        max_y2 = np.max(dati_n2_resampled)
        ax_destro_y2.set_ylim(min_y2, max_y2)
    plt.suptitle(r.identifiers["strategy"] + " (" + r.identifiers["axis_pre"] + ") " + ", " + r.identifiers[
        "specfile"] + ", scenario=" + r.identifiers["mab-rtk-contextual-scenarios"])
    plt.tight_layout()
    fig.tight_layout()

    graphs_ctr += 1
    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + ".svg"))
    fig.clf()
    
