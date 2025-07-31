import os
import sys
from datetime import datetime

from matplotlib import pyplot as plt
from numpy import arange
import numpy as np
from scipy.interpolate import interp1d
from issue12_plots_copia import *
from conf import EXPIRATION_TIMEOUT

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _api.datarecords import (extract_datarecords_from_exp_name, extract_result_dict_from_datarecord,
                              extract_timeseries_from_result_single, extract_timeseries_from_result_multiple,
                              filter_datarecords_by_specfiles
                              )
from _internal import consts, utils


# raccogli i dati delle istanze
records=extract_datarecords_from_exp_name("mem-debug")

timestamp = datetime.now().replace(microsecond=0)
graphs_ctr=0
# TODO ma i times servono? anche come salvati, per forza?
# per ogni istanza fai roba:
trace_iat=[]
tempi_transizioni=[]
valori_plot=[]
mem=[]
instances=[]


def converti_traccia(tempi_n1):
    # Converti la lista 'time' in un array NumPy
    # --- Resampling della seconda serie dati ---
    # 1. Crea un array di "tempi" impliciti per la seconda serie dati
    tempi_n2_impliciti = np.linspace(tempi_n1.min(), tempi_n1.max(),
                                     len(tempi_transizioni))  # Stesso intervallo di tempi_n1, ma lunghezza di tempi_transizioni
    # 2. Crea l'asse dei tempi di destinazione (basato su time)
    tempi_destinazione = np.linspace(tempi_n1.min(), tempi_n1.max(), len(tempi_n1))
    # 3. Crea una funzione di interpolazione basata sui "tempi" impliciti e i valori della seconda serie
    funzione_interpolazione = interp1d(tempi_n2_impliciti, tempi_transizioni, kind='linear', fill_value="extrapolate")
    # 4. Usa la funzione di interpolazione per ottenere i nuovi valori della seconda serie ai tempi della prima
    dati_n2_resampled = funzione_interpolazione(tempi_destinazione)
    return tempi_destinazione, dati_n2_resampled


for r in records:
    trace_iat=[]
    tempi_transizioni=[]
    valori_plot=[]
    mem=[]
    instances=[]
    path=""
    print("RECORD", r.identifiers["axis_post"])
    tracename=r.identifiers["specfile"]
    if tracename=="sfasate_sinusoid": tracename="sinus_delay0"
    if tracename=="sfasate_bell": tracename="bell_delay0"
    if "specbase" in tracename:
        tempi_transizioni=[0,0,0]
        valori_plot=[0,0,0]
    else:
        print("UUUUUUUUUUU")
        path=os.path.abspath("_traces/"+tracename
                             .replace("_f1", "")
                             .replace("_f2", "")
                             .replace("_f3", "")
                             .replace("_f4", "")
                             .replace("_f5", "")
                             .replace("_x5", "")
                             .replace("_full", "")
+"_rates.iat")
        print(path)
        if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        tempi_transizioni.append(float(line))
        """path=os.path.abspath("_traces/"+tracename+"_rates.iat")
             if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        print(line)
                        valori_plot.append(float(line))
        """
    mem = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys")
    memact = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys")
    availMem = extract_result_dict_from_datarecord(r, "availableMemory_sys")
    instances = extract_result_dict_from_datarecord(r, "instance_invoked")
    time = extract_result_dict_from_datarecord(r, "time")
    policies = extract_result_dict_from_datarecord(r, "policy")
    drops = extract_result_dict_from_datarecord(r, "drops_sys")
    dropsp = extract_result_dict_from_datarecord(r, "drops_perc_sys")
    util_sys_new = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys_RESAMPLED")
    mw = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys_MW")
    samples = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys_SAMPLES")
    samplesact = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys_SAMPLES")
    actMW = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys_MW")
    #util_sys_act_new = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys_SAMPLES")
    thr = extract_result_dict_from_datarecord(r, "throughput_sys")


#############################################################à

    #fig, (ax1, ax_destro) = plt.subplots(2, 2, figsize=(12, 6))
    fig, ax = plt.subplots(2, 3, figsize=(20, 8))

    ax_00 = ax[0, 0]
    ax_01 = ax[0, 1]
    ax_02 = ax[0, 2]
    ax_10 = ax[1, 0]
    ax_11 = ax[1, 1]
    ax_12 = ax[1, 2]


    # 00: traccia

    tempi_n1 = np.array(time)
    #tempi_destinazione=[]
    print("TRACENAME", tracename)
    if os.path.exists(path):

        pass
    traccia_x, traccia_y=converti_traccia(tempi_n1)
    #traccia_x=time
    #traccia_y=tempi_transizioni
    print("TS", tempi_transizioni)
    # Plotta la stessa serie resampled anche nel grafico di destra (ax_destro)
    #ax_destro.plot(tempi_destinazione, dati_convertiti,  drawstyle='steps-post', linestyle='--', linewidth=0.7)
    #ax_destro.tick_params(axis='y', labelcolor=color)

    COLOR_TRACE="blue"
    COLOR_SAMPLES="purple"
    COLOR_BAD="red"
    COLOR_GOOD="green"
    COLOR_OLD="silver"
    COLOR_NEW="orange"
    COLOR_MEM="black"


    ax_00.set_title("Traccia")
    ax_00.set_xlabel('Tempo [s]')
    ax_00.set_ylabel('Frequenza arrivi (traccia) [req/s]')

    ax_00.plot(traccia_x, traccia_y, drawstyle='steps-post', linestyle='--', linewidth=0.7, label="Traccia", color=COLOR_TRACE)
    #ax_00.tick_params(axis='y')


    ax_00.legend()



    # 01: utilizzazioni

    #color = 'tab:red'
    ax_01.set_title("Utilizz. memoria TOTALE (container attivi + warm)")
    ax_01.set_xlabel('Tempo [s]')
    ax_01.set_ylabel('avgMemoryUtilization')
    ax_01.set_ylim([0, 1])
    # Plotta i dati per ciascuna label

    ax_01.scatter(time, samples, marker='x', label="campioni", color=COLOR_SAMPLES)#, label=f'pallini: post-init')
    ax_01.scatter(time, mem, marker='d', label="preesistente", color=COLOR_OLD, s=20)#, label=f'pallini: post-init')
    #ax1.scatter(time, memact, marker='o', label="actMem")#, label=f'pallini: post-init')
    #ax_01.scatter(time, util_sys_new, marker='o', label="RESAMPLED")#, label=f'pallini: post-init')
    ax_01.scatter(time, mw, marker='o', label="nuova", color=COLOR_NEW)#, label=f'pallini: post-init')
    #ax1.scatter(time, util_sys_act_new, marker='o', label="util_sys_act_new")#, label=f'pallini: post-init')

    #ax1.plot(t, data1, color=color)
    ax_01.tick_params(axis='y')
    ax_01.legend()

    #ax2 = ax_00.twinx()  # instantiate a second Axes that shares the same x-axis




    # 02: utilizzazioni ACTIVE
    ax_02.set_title("Utilizz. memoria ATTIVA (solo ctr. attivi, NO warm)")
    ax_02.set_xlabel('Tempo [s]')
    ax_02.set_ylabel('avgMemoryUtilization')
    ax_02.set_ylim([0, 1])
    ax_02.scatter(time, samplesact, marker='x', label="campioni", color=COLOR_SAMPLES)#, label=f'pallini: post-init')
    ax_02.scatter(time, memact, marker='d', label="preesistente", color=COLOR_OLD, s=20)#, label=f'pallini: post-init')
    ax_02.scatter(time, actMW, marker='o', label="nuova", color=COLOR_NEW)#, label=f'pallini: post-init')
    #ax_02.scatter(time, samplesact, marker='o', label="util_sys_act_new")#, label=f'pallini: post-init')
    ax_02.legend()





    # 10: drops
    ax_10.set_title("Percentuale drops")
    ax_10.set_xlabel('Tempo [s]')
    ax_10.set_ylabel('drops (%)')
    ax_10.set_ylim([0, 1])
    ax_10.scatter(time, dropsp, marker='o', label="drops%", color=COLOR_BAD)#, label=f'pallini: post-init')
    ax_10.legend()


    # 11: throughput
    ax_11.set_title("Arrivi vs Throughput vs Drops")
    ax_11.set_xlabel('Tempo [s]')
    ax_11.set_ylabel('Frequenza [req/s]')
    ax_11.plot(traccia_x, traccia_y, drawstyle='steps-post', linestyle='--', linewidth=0.7, label="Traccia", color=COLOR_TRACE)
    ax_11.scatter(time, thr, marker='o', label="Throughput", color=COLOR_GOOD)#, label=f'pallini: post-init')
    ax_11.scatter(time, drops, marker='o', label="Drops", color=COLOR_BAD)#, label=f'pallini: post-init')
    ax_11.legend()

    # 12: availmem
    ax_12.set_title("Memoria totale disponibile")
    ax_12.set_xlabel('Tempo [s]')
    ax_12.set_ylabel('Memoria disponibile')
    ax_12.axhline(y=144000, color='red', linestyle='--', linewidth=1, label="Memoria totale")
    ax_12.set_ylim([0, 144500])
    ax_12.scatter(time, availMem, marker='o', label="Memoria disponibile", color=COLOR_MEM)#, label=f'pallini: post-init')
    ax_12.legend()

    #fig.tight_layout()
    plt.suptitle(r.identifiers["strategy"]+" ("+r.identifiers["axis_pre"]+") "+", "+r.identifiers["specfile"])

    #plt.legend()
    plt.tight_layout()
    fig.tight_layout()
    #plt.show()

    #fig.title(r.identifiers["axis_pre"]+" "+r.identifiers["strategy"]+" "+r.identifiers["specfile"]+" "+tracename)



    graphs_ctr += 1
    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + ".svg"))
    fig.clf()

    #graph_availMem(availMem, time, "linear-debug", ["600"])