import conf
import numpy as np
import math
from lp_optimizer import compute_deadline_satisfaction_probs

def update_probabilities (local, cloud, aggregated_edge_memory, functions,
                            classes,
                          arrival_rates,
                          serv_time, serv_time_cloud, serv_time_edge,
                          init_time_local, init_time_cloud, init_time_edge,
                          offload_time_cloud, offload_time_edge,
                          bandwidth_cloud, bandwidth_edge,
                          cold_start_p_local, cold_start_p_cloud,
                          cold_start_p_edge,budget=-1,
                          local_usable_memory_coeff=1.0, VERBOSE=False):
    F = functions
    C = classes
    FC = [(f,c) for f in F for c in C]

    p = np.zeros((3, len(FC)))

    pDeadlineL, pDeadlineC, pDeadlineE = compute_deadline_satisfaction_probs(FC, serv_time, serv_time_cloud, serv_time_edge,\
                          init_time_local, init_time_cloud, init_time_edge,\
                          offload_time_cloud, offload_time_edge,\
                          bandwidth_cloud, bandwidth_edge,\
                          cold_start_p_local, cold_start_p_cloud, cold_start_p_edge)


    #prob += (pl.lpSum([c.utility*arrival_rates[(f,c)]*\
    #                   (pL[f][c]*deadline_satisfaction_prob_local[(f,c)]+\
    #                   pE[f][c]*deadline_satisfaction_prob_edge[(f,c)]+\
    #                   pC[f][c]*deadline_satisfaction_prob_cloud[(f,c)]) for f,c in F_C]) -\
    #                   pl.lpSum([c.penalty*arrival_rates[(f,c)]*\
    #                   (pL[f][c]*(1.0-deadline_satisfaction_prob_local[(f,c)])+\
    #                   pE[f][c]*(1.0-deadline_satisfaction_prob_edge[(f,c)])+\
    #                   pC[f][c]*(1.0-deadline_satisfaction_prob_cloud[(f,c)])) for f,c in F_C])-\
    #            BETA_COST*pl.lpSum([cloud.cost*arrival_rates[(f,c)]*\
    #                   pC[f][c]*serv_time_cloud[f]*f.memory/1024 for f,c in F_C]) , "objUtilCost")



    probs = {(fc[0],fc[1]): [p[0,i], p[1,i], p[2,i], 1-p[0,i]-p[1,i]-p[2,i]]
                     for i,fc in enumerate(FC)}


    # Workaround to avoid numerical issues
    for f,c in FC:
        s = sum(probs[(f,c)])
        probs[(f,c)] = [x/s for x in probs[(f,c)]]
        if VERBOSE > 0:
            print(f"{f}-{c}: {probs[(f,c)]}")

    return probs
