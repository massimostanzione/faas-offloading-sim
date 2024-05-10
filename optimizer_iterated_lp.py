import conf
import numpy as np
import math
import lp_optimizer 
from optimization import OptProblemParams, Optimizer

METHOD_ADAPTIVE_UTIL="adaptive-util"
METHOD_GREEDY_REDUCTION="greedy-reduction"

class IteratedLPOptimizer (Optimizer):

    def __init__ (self, method=METHOD_ADAPTIVE_UTIL, max_p_block=0.01, verbose=False):
        super().__init__(verbose)
        self.method = method
        self.max_p_block = max_p_block



    def optimize_probabilities (self, params: OptProblemParams):
        F = params.functions
        C = params.classes

        FC=list(params.fun_classes())
        N=len(FC)
        EDGE_ENABLED = True if params.aggregated_edge_memory > 0.0 else False

        pDeadlineL, pDeadlineC, pDeadlineE = lp_optimizer.compute_deadline_satisfaction_probs(params)


        def kaufman (sol):
            M = int(params.local_node.total_memory)
            mem_demands = [fc[0].memory for fc in FC]
            alpha = np.zeros(len(mem_demands))
            for i,fc in enumerate(FC):
                alpha[i] = params.arrival_rates[fc]*sol[fc][0]*params.serv_time_local[fc[0]]

            q = np.zeros(M+1)
            q[0] = 1
            for j in range(1, M+1):
                for i,m in enumerate(mem_demands):
                    if j-m < 0:
                        continue
                    q[j] += q[j-m] * m * alpha[i]
                q[j] /= j


            G = np.sum(q)

            bp_per_fun = np.zeros(len(FC))
            for i,m in enumerate(mem_demands):
                for j in range(0, m):
                    if M-j >= 0:
                        bp_per_fun[i] += q[M - j]
            bp_per_fun /= G
            return bp_per_fun

        def obj (_p):
            blocking_p = kaufman(_p)
            v = 0
            for i,fc in enumerate(FC):
                f,c = fc
                gammaL = c.utility*pDeadlineL[fc] - c.deadline_penalty*(1-pDeadlineL[fc]) + c.drop_penalty
                gammaC = c.utility*pDeadlineC[fc] - c.deadline_penalty*(1-pDeadlineC[fc]) + c.drop_penalty
                gammaE = c.utility*pDeadlineE[fc] - c.deadline_penalty*(1-pDeadlineE[fc]) + c.drop_penalty
                v += params.arrival_rates[(f,c)] * (\
                        _p[fc][0]*(1-blocking_p[i])*gammaL +\
                        _p[fc][1]*gammaC)
                if EDGE_ENABLED:
                    v += params.arrival_rates[(f,c)] * _p[fc][2]*gammaE
            return v


        opt = lp_optimizer.LPOptimizer(verbose=False)

        if self.method == METHOD_ADAPTIVE_UTIL:
            uLow=0.01
            uHigh=1.0

            pblock=1.0
            bestU=None
            bestSol=None
            while uHigh - uLow > 0.001:
                u = uLow + (uHigh-uLow)/2
                params.usable_local_memory_coeff = u
                sol, _ = opt.optimize_probabilities(params)
                pblock = max(kaufman(sol))
                obj_val = obj(sol)
                #print(f"uH={uHigh} uL={uLow} pblock={pblock}; obj={obj_val}")

                # TODO: try reasoning in terms of lost utility?
                if pblock > self.max_p_block:
                    uHigh = u
                else:
                    uLow = u
                    if bestU is None or u > bestU:
                        bestU = u
                        bestSol = sol

            probs = bestSol
        elif self.method == METHOD_GREEDY_REDUCTION:
            probs, _ = opt.optimize_probabilities(params)
            pblock = kaufman(probs)

            while max(pblock) > 0.01:
                mem_demands = np.array([fc[0].memory*params.arrival_rates[fc]*probs[fc][0]*(1-pblock[i]) for i,fc in enumerate(FC)])
                utilities = np.array([fc[1].utility*pDeadlineL[fc] - fc[1].deadline_penalty*(1-pDeadlineL[fc]) + fc[1].drop_penalty for fc in FC])
                dem_util_ratio = utilities/mem_demands
                i = np.argmin(dem_util_ratio)
                i = np.argmax(mem_demands)
                probs[FC[i]][0]*=0.9
                pblock = kaufman(probs)
                print(pblock)
                print(probs)

            # Solve LP fixing local exec probabilities
            probs, _ = opt.optimize_probabilities(params, fixed_local_probs=probs)

            obj_val = obj(probs)
        print(obj_val)


        #Workaround to avoid numerical issues
        for f,c in params.fun_classes():
            for i,_p in enumerate(probs[(f,c)]):
                if _p < 0.0001:
                    probs[(f,c)][i] = 0
            s = sum(probs[(f,c)])
            probs[(f,c)] = [x/s for x in probs[(f,c)]]
            if self.verbose > 0:
                print(f"{f}-{c}: {probs[(f,c)]}")


        return probs, obj_val
