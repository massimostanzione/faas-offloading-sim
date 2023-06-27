import os
import math
import sys
import pulp as pl

warm_start = False

def update_probabilities (local, cloud, aggregated_edge_memory, sim,
                          arrival_rates,
                          serv_time, serv_time_cloud, serv_time_edge,
                          init_time,
                          offload_time_cloud, offload_time_edge,
                          cold_start_p_local, cold_start_p_cloud,
                          cold_start_p_edge):
    F = sim.functions
    C = sim.classes
    F_C = [(f,c) for f in F for c in C]

    prob = pl.LpProblem("MyProblem", pl.LpMaximize)
    x = pl.LpVariable.dicts("X", (F, C), 0, None, pl.LpContinuous)
    y = pl.LpVariable.dicts("Y", (F, C), 0, None, pl.LpContinuous)
    pL = pl.LpVariable.dicts("PExec", (F, C), 0, 1, pl.LpContinuous)
    pC = pl.LpVariable.dicts("PCloud", (F, C), 0, 1, pl.LpContinuous)
    pE = pl.LpVariable.dicts("PEdge", (F, C), 0, 1, pl.LpContinuous)
    pD = pl.LpVariable.dicts("PDrop", (F, C), 0, 1, pl.LpContinuous)

    deadline_satisfaction_prob_local = {}
    deadline_satisfaction_prob_edge = {}
    deadline_satisfaction_prob_cloud = {}

    # TODO: we are assuming exponential distribution
    # Probability of satisfying the deadline
    for f,c in F_C:
        p = 0.0
        if c.max_rt - init_time > 0.0:
            p += cold_start_p_local[f]*(1.0 - math.exp(-1.0/serv_time[f]*(c.max_rt - init_time)))
        if c.max_rt > 0.0:
            p += (1.0-cold_start_p_local[f])*(1.0 - math.exp(-1.0/serv_time[f]*c.max_rt))
        deadline_satisfaction_prob_local[(f,c)] = p

        p = 0.0
        if c.max_rt - init_time - offload_time_cloud > 0.0:
            p += cold_start_p_cloud[f]*(1.0 - math.exp(-1.0/serv_time_cloud[f]*(c.max_rt - init_time - offload_time_cloud)))
        if c.max_rt - offload_time_cloud > 0.0:
            p += (1.0-cold_start_p_cloud[f])*(1.0 - math.exp(-1.0/serv_time_cloud[f]*(c.max_rt-offload_time_cloud)))
        deadline_satisfaction_prob_cloud[(f,c)] = p

        p = 0.0
        if c.max_rt - init_time - offload_time_edge > 0.0:
            p += cold_start_p_edge[f]*(1.0 - math.exp(-1.0/serv_time_edge[f]*(c.max_rt - init_time - offload_time_edge)))
        if c.max_rt - offload_time_edge > 0.0:
            p += (1.0-cold_start_p_edge[f])*(1.0 - math.exp(-1.0/serv_time_edge[f]*(c.max_rt-offload_time_edge)))
        deadline_satisfaction_prob_edge[(f,c)] = p

    #print("Sat prob C:")
    #print(deadline_satisfaction_prob_cloud)
    #print(offload_time_cloud)
    #print(serv_time_cloud)
    #print("Sat prob E:")
    #print(deadline_satisfaction_prob_edge)
    #print(offload_time_edge)
    #print(serv_time_edge)

    prob += (pl.lpSum([c.utility*arrival_rates[(f,c)]*\
                       (pL[f][c]*deadline_satisfaction_prob_local[(f,c)]+\
                       pE[f][c]*deadline_satisfaction_prob_edge[(f,c)]+\
                       pC[f][c]*deadline_satisfaction_prob_cloud[(f,c)]) for f,c in F_C]) -\
                pl.lpSum([cloud.cost*arrival_rates[(f,c)]*\
                       pC[f][c]*serv_time_cloud[f]*f.memory/1024 for f,c in F_C]) , "objUtilCost")

    # Probability
    for f,c in F_C:
        prob += (pL[f][c] + pE[f][c] + pC[f][c] + pD[f][c] == 1.0)

    # Memory
    prob += (pl.lpSum([f.memory*x[f][c] for f,c in F_C]) <= local.total_memory)
    prob += (pl.lpSum([f.memory*y[f][c] for f,c in F_C]) <= aggregated_edge_memory)

    # Share
    for f,c in F_C:
        prob += (pL[f][c]*arrival_rates[(f,c)]*serv_time[f] <= x[f][c])
        prob += (pE[f][c]*arrival_rates[(f,c)]*serv_time_edge[f] <= y[f][c])

    class_arrival_rates = {}
    for c in C:
        class_arrival_rates[c] = sum([arrival_rates[(f,c)] for f in F if c in C])

    # Min completion
    for c in C:
        if c.min_completion_percentage > 0.0 and class_arrival_rates[c] > 0.0:
            prob += (pl.lpSum([pD[f][c]*arrival_rates[(f,c)] for f in F])/class_arrival_rates[c]                     <= 1 - c.min_completion_percentage)


    status = solve(prob)
    if status != "Optimal":
        print(f"WARNING: solution status: {status}")
        return None

    print("Obj = ", pl.value(prob.objective))
    shares = {(f,c): pl.value(x[f][c]) for f,c in F_C}
    print(f"Shares: {shares}")

    probs = {(f,c): [pl.value(pL[f][c]),
                     pl.value(pC[f][c]),
                     pl.value(pE[f][c]),
                     pl.value(pD[f][c])] for f,c in F_C}

    # Workaround to avoid numerical issues
    for f,c in F_C:
        print(f"{f}-{c}: {probs[(f,c)]}")
        s = sum(probs[(f,c)])
        probs[(f,c)] = [x/s for x in probs[(f,c)]]
    return probs

def solve (problem):
    global warm_start
    solver_name = os.environ.get("PULP_SOLVER", "GLPK_CMD")
    
    if not solver_name in ["CPLEX_CMD", "GUROBI_CMD", "PULP_CBC_CMD", "CBC_CMD", "CPLEX_PY", "GUROBI"] and warm_start:
        print("WARNING: warmStart not supported by solver {}".format(solver_name))
        warm_start = False

    if not warm_start:
        if solver_name == "GUROBI_CMD":
            solver = pl.getSolver(solver_name, gapRel=0.02, timeLimit=900)
        else:
            solver = pl.getSolver(solver_name, msg=False)
    else:
        solver = pl.getSolver(solver_name, warmStart=warm_start)

    problem.solve(solver)
    return pl.LpStatus[problem.status]


