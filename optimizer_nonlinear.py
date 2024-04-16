import conf
import numpy as np
import math
import lp_optimizer 

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

    lp_probs = lp_optimizer.update_probabilities(local, cloud, aggregated_edge_memory, functions,
                            classes, arrival_rates, serv_time, serv_time_cloud, serv_time_edge,
                          init_time_local, init_time_cloud, init_time_edge,
                          offload_time_cloud, offload_time_edge,
                          bandwidth_cloud, bandwidth_edge,
                          cold_start_p_local, cold_start_p_cloud,
                          cold_start_p_edge,budget, local_usable_memory_coeff)


    for i,fc in enumerate(FC):
        p[0,i] = lp_probs[fc][0]
        p[1,i] = lp_probs[fc][1]
        p[2,i] = lp_probs[fc][2]


    pDeadlineL, pDeadlineC, pDeadlineE = lp_optimizer.compute_deadline_satisfaction_probs(FC, serv_time, serv_time_cloud, serv_time_edge,\
                          init_time_local, init_time_cloud, init_time_edge,\
                          offload_time_cloud, offload_time_edge,\
                          bandwidth_cloud, bandwidth_edge,\
                          cold_start_p_local, cold_start_p_cloud, cold_start_p_edge)

    def kaufman (_p):
        M = int(local_usable_memory_coeff*local.total_memory)
        mem_demands = [fc[0].memory for fc in FC]
        alpha = np.zeros(len(mem_demands))
        for i,fc in enumerate(FC):
            alpha[i] = arrival_rates[fc]*_p[0,i]*serv_time[fc[0]]

        q = np.zeros(M+1)
        q[0] = 1
        for j in range(1, M+1):
            for i,m in enumerate(mem_demands):
                q[j] += q[j-m] * m * alpha[i]
            q[j] /= j


        G = np.sum(q)

        bp_per_fun = np.zeros(len(FC))
        for i,m in enumerate(mem_demands):
            for j in range(0, m):
                bp_per_fun[i] += q[M - j]
        bp_per_fun /= G
        return bp_per_fun



    def lp_obj (_p):
        v = 0
        for i,fc in enumerate(FC):
            f,c = fc
            gammaL = c.utility*pDeadlineL[fc] - c.penalty*(1-pDeadlineL[fc])
            gammaC = c.utility*pDeadlineC[fc] - c.penalty*(1-pDeadlineC[fc])
            gammaE = c.utility*pDeadlineE[fc] - c.penalty*(1-pDeadlineE[fc])
            v += arrival_rates[(f,c)] * (_p[0,i]*gammaL + _p[1,i]*gammaC + _p[2,i]*gammaE)
        return v

    def obj (_p):
        blocking_p = kaufman(_p)
        print(blocking_p)
        v = 0
        for i,fc in enumerate(FC):
            f,c = fc
            gammaL = c.utility*pDeadlineL[fc] - c.penalty*(1-pDeadlineL[fc])
            gammaC = c.utility*pDeadlineC[fc] - c.penalty*(1-pDeadlineC[fc])
            gammaE = c.utility*pDeadlineE[fc] - c.penalty*(1-pDeadlineE[fc])
            v += arrival_rates[(f,c)] * (\
                    _p[0,i]*(1-blocking_p[i])*gammaL +\
                    _p[1,i]*gammaC + _p[2,i]*gammaE)
        return v

    print(f"LP obj: {obj(p)} ({lp_obj(p)})")

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



    probs = {(fc[0],fc[1]): [p[0,i], p[1,i], p[2,i], max(0.0,1.0-p[0,i]-p[1,i]-p[2,i])]
                     for i,fc in enumerate(FC)}


    #Workaround to avoid numerical issues
    for f,c in FC:
        s = sum(probs[(f,c)])
        probs[(f,c)] = [x/s for x in probs[(f,c)]]
        if VERBOSE > 0:
            print(f"{f}-{c}: {probs[(f,c)]}")


    return probs
