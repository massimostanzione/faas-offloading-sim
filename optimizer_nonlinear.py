import conf
import numpy as np
import math
import lp_optimizer 
from scipy.optimize import minimize, LinearConstraint
from optimization import OptProblemParams, Optimizer

INITIAL_GUESS_NONE=None
INITIAL_GUESS_LP="lp"
INITIAL_GUESS_LAST_SOL="last"


DUMP_SOL=False

def dump_solution (filename, x, EDGE_ENABLED):
    i=0
    j=0
    with open(filename, "w") as of:
        while i < x.shape[0]:
            print(f"pL-{j}, {x[i]}", file=of)
            print(f"pC-{j}, {x[i+1]}", file=of)
            if EDGE_ENABLED:
                print(f"pE-{j}, {x[i+2]}", file=of)
            i+=3 if EDGE_ENABLED else 2
            j+=1

class NonlinearOptimizer (Optimizer):

    def __init__ (self, initial_guess="lp", method="trust-region",
            use_lp_for_bounds=False, blocking_approximation=None, verbose=False):
        super().__init__(verbose)
        self.initial_guess = initial_guess
        self.method = method
        self.last_solution = None
        self.use_lp_for_bounds = use_lp_for_bounds
        self.blocking_approximation = blocking_approximation
        if self.blocking_approximation is not None and (self.blocking_approximation == "" or self.blocking_approximation.lower() == "none"):
            self.blocking_approximation = None


    def optimize (self, params, pDeadlineL, pDeadlineC, pDeadlineE, x0=None, lp_probs=None):
        FC=list(params.fun_classes())
        N=len(FC)
        EDGE_ENABLED = True if params.aggregated_edge_memory > 0.0 else False
        NVARS = 3 if EDGE_ENABLED else 2

        assert(lp_probs is not None or (not self.use_lp_for_bounds))

        if x0 is None:
            x0 = np.zeros(NVARS*N)
            if lp_probs is not None:
                # Load the LP solution as the initial point
                for i,fc in enumerate(FC):
                    x0[NVARS*i+0] = lp_probs[fc][0]
                    x0[NVARS*i+1] = lp_probs[fc][1]
                    if EDGE_ENABLED:
                        x0[NVARS*i+2] = lp_probs[fc][2]

        if DUMP_SOL:
            dump_solution("guesslinear.txt", x0, EDGE_ENABLED)
            x0 = np.zeros(NVARS*N) # for debugging


        def kaufman (_p):
            plocal = _p[0::NVARS]
            return _kaufman(plocal)

        def _kaufman (plocal):
            M = int(params.usable_local_memory_coeff*params.local_node.total_memory)
            mem_demands = [fc[0].memory for fc in FC]
            alpha = np.zeros(len(mem_demands))
            for i,fc in enumerate(FC):
                alpha[i] = params.arrival_rates[fc]*plocal[i]*params.serv_time_local[fc[0]]

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



        def lp_obj (_p):
            v = 0
            for i,fc in enumerate(FC):
                f,c = fc
                gammaL = c.utility*pDeadlineL[fc] - c.deadline_penalty*(1-pDeadlineL[fc]) + c.drop_penalty
                gammaC = c.utility*pDeadlineC[fc] - c.deadline_penalty*(1-pDeadlineC[fc]) + c.drop_penalty
                gammaE = c.utility*pDeadlineE[fc] - c.deadline_penalty*(1-pDeadlineE[fc]) + c.drop_penalty
                v += params.arrival_rates[(f,c)] * (_p[NVARS*i]*gammaL + _p[NVARS*i+1]*gammaC)
                if EDGE_ENABLED:
                    v += params.arrival_rates[(f,c)] * _p[NVARS*i+2]*gammaE
            return v

        def obj (_p):
            blocking_p = kaufman(_p)
            v = 0
            for i,fc in enumerate(FC):
                f,c = fc
                gammaL = c.utility*pDeadlineL[fc] - c.deadline_penalty*(1-pDeadlineL[fc]) + c.drop_penalty
                gammaC = c.utility*pDeadlineC[fc] - c.deadline_penalty*(1-pDeadlineC[fc]) + c.drop_penalty
                gammaE = c.utility*pDeadlineE[fc] - c.deadline_penalty*(1-pDeadlineE[fc]) + c.drop_penalty
                v += params.arrival_rates[(f,c)] * (\
                        _p[NVARS*i]*(1-blocking_p[i])*gammaL +\
                        _p[NVARS*i+1]*gammaC)
                if EDGE_ENABLED:
                    v += params.arrival_rates[(f,c)] * _p[NVARS*i+2]*gammaE
            return v


        def is_feasible (x):
            print(x)
            for i,fc in enumerate(FC):
                s = x[NVARS*i] + x[NVARS*i+1]
                if EDGE_ENABLED:
                    s += x[NVARS*i+2]
                if s > 1.001:
                    print(x)
                    print(f"Sum: {s}")
                    return False
            # cloud usage
            total=0
            for i,fc in enumerate(FC):
                total += x[NVARS*i+1]*params.cloud.cost*params.arrival_rates[fc]*params.serv_time_cloud[fc[0]]*fc[0].memory/1024
            if params.budget > 0 and params.budget/3600 < total - 0.001:
                print("Budget")
                return False
            if EDGE_ENABLED:
                total=0
                for i,fc in enumerate(FC):
                    total += x[NVARS*i+2]*params.arrival_rates[fc]*params.serv_time_edge[fc[0]]*fc[0].memory
                if params.aggregated_edge_memory < total - 0.001:
                    return False
            return True

        print(f"LP obj for x0: {obj(x0)} ({lp_obj(x0)})")

        if self.blocking_approximation == "linear":
            from sklearn import datasets, linear_model
            from sklearn.metrics import mean_squared_error, r2_score

            Ntrain=5
            coeffs = np.random.random_sample(Ntrain*N).reshape(Ntrain,N)
            lp_local_probs = np.zeros(N)
            for i,fc in enumerate(FC):
                lp_local_probs[i] = lp_probs[fc][0]
            X = coeffs*lp_local_probs
            Y = np.zeros((Ntrain,N))
            for i in range(Ntrain):
                Y[i,:] = _kaufman(X[i,:])

            # Create linear regression object
            regr = linear_model.LinearRegression()
            regr.fit(X, Y)

            def approx_obj (_p):
                blocking_p = regr.predict(_p[0::NVARS].reshape(1,-1))[0]
                v = 0
                for i,fc in enumerate(FC):
                    f,c = fc
                    gammaL = c.utility*pDeadlineL[fc] - c.deadline_penalty*(1-pDeadlineL[fc]) + c.drop_penalty
                    gammaC = c.utility*pDeadlineC[fc] - c.deadline_penalty*(1-pDeadlineC[fc]) + c.drop_penalty
                    gammaE = c.utility*pDeadlineE[fc] - c.deadline_penalty*(1-pDeadlineE[fc]) + c.drop_penalty
                    v += params.arrival_rates[(f,c)] * (\
                            _p[NVARS*i]*(1-blocking_p[i])*gammaL +\
                            _p[NVARS*i+1]*gammaC)
                    if EDGE_ENABLED:
                        v += params.arrival_rates[(f,c)] * _p[NVARS*i+2]*gammaE
                return v
        elif self.blocking_approximation == "poly":
            from sklearn import datasets, linear_model
            from sklearn.metrics import mean_squared_error, r2_score
            from sklearn.preprocessing import PolynomialFeatures

            Ntrain=10
            coeffs = np.random.random_sample(Ntrain*N).reshape(Ntrain,N)
            lp_local_probs = np.zeros(N)
            for i,fc in enumerate(FC):
                lp_local_probs[i] = lp_probs[fc][0]
            X = coeffs*lp_local_probs
            Y = np.zeros((Ntrain,N))
            for i in range(Ntrain):
                Y[i,:] = _kaufman(X[i,:])

            poly = PolynomialFeatures(degree=3, include_bias=True) 
            X2 = poly.fit_transform(X)

            # Create linear regression object
            regr = linear_model.LinearRegression()
            regr.fit(X2, Y)

            def approx_obj (_p):
                x = poly.transform(_p[0::NVARS].reshape(1,-1))
                blocking_p = regr.predict(x)[0]
                v = 0
                for i,fc in enumerate(FC):
                    f,c = fc
                    gammaL = c.utility*pDeadlineL[fc] - c.deadline_penalty*(1-pDeadlineL[fc]) + c.drop_penalty
                    gammaC = c.utility*pDeadlineC[fc] - c.deadline_penalty*(1-pDeadlineC[fc]) + c.drop_penalty
                    gammaE = c.utility*pDeadlineE[fc] - c.deadline_penalty*(1-pDeadlineE[fc]) + c.drop_penalty
                    v += params.arrival_rates[(f,c)] * (\
                            _p[NVARS*i]*(1-blocking_p[i])*gammaL +\
                            _p[NVARS*i+1]*gammaC)
                    if EDGE_ENABLED:
                        v += params.arrival_rates[(f,c)] * _p[NVARS*i+2]*gammaE
                return v




        bounds = [(0,1) for i in range(NVARS*N)]

        if self.use_lp_for_bounds:
            for i,fc in enumerate(FC):
                bounds[NVARS*i] = (0,lp_probs[fc][0])

        if self.method == "trust-region":
            # sum <= 1
            A = np.zeros((N, NVARS*N))
            for i in range(N):
                A[i,NVARS*i]=1
                A[i,NVARS*i+1]=1
                if EDGE_ENABLED:
                    A[i,NVARS*i+2]=1
            sumLC = LinearConstraint(A=A, lb=0, ub=1, keep_feasible=False)
            
            if params.budget > 0:
                A2 = np.zeros(NVARS*N)
                for i,fc in enumerate(FC):
                    # cloud usage
                    A2[NVARS*i+1]=params.cloud.cost*params.arrival_rates[fc]*params.serv_time_cloud[fc[0]]*fc[0].memory/1024
                budgetLC = LinearConstraint(A=A2, lb=0, ub=params.budget/3600, keep_feasible=False)

                constraints = [sumLC, budgetLC]
            else:
                constraints = [sumLC]
            
            if EDGE_ENABLED:
                A3 = np.zeros(NVARS*N)
                for i,fc in enumerate(FC):
                    # edge mem
                    A3[NVARS*i+2]=params.arrival_rates[fc]*params.serv_time_edge[fc[0]]*fc[0].memory
                edgeMemLC = LinearConstraint(A=A3, lb=0, ub=params.aggregated_edge_memory, keep_feasible=False)
                constraints.append(edgeMemLC)

            fobj=obj if self.blocking_approximation is None else approx_obj
            res = minimize(lambda x: -1*fobj(x), x0, method="trust-constr", bounds=bounds, constraints=constraints, tol=1e-6, options={"maxiter": 200000})
            print(res)
            x = res.x
            obj_val = obj(x)
        elif self.method == "slsqp":
            constraints = []
            for i in range(N):
                # sum <= 1
                if EDGE_ENABLED:
                    c = lambda x, i=i: 1-x[NVARS*i]-x[NVARS*i+1]-x[NVARS*i+2]
                else:
                    c = lambda x, i=i: 1-x[NVARS*i]-x[NVARS*i+1]
                constraints.append({"type":"ineq", "fun": c})

            # cloud usage
            def cbudget(x):
                total=0
                for i,fc in enumerate(FC):
                    total += x[NVARS*i+1]*params.cloud.cost*params.arrival_rates[fc]*params.serv_time_cloud[fc[0]]*fc[0].memory/1024
                return params.budget/3600-total
            if params.budget > 0:
                constraints.append({"type":"ineq", "fun": cbudget})

            if EDGE_ENABLED:
                def cedge(x):
                    total=0
                    for i,fc in enumerate(FC):
                        total += x[NVARS*i+2]*params.arrival_rates[fc]*params.serv_time_edge[fc[0]]*fc[0].memory
                    return params.aggregated_edge_memory-total
                constraints.append({"type":"ineq", "fun": cedge})

            fobj=obj if self.blocking_approximation is None else approx_obj
            res = minimize(lambda x: -1*fobj(x), x0, method="SLSQP", bounds=bounds, constraints=constraints, tol=1e-6, options={"maxiter": 200000})
            print(res)
            x = res.x
            obj_val = obj(x)

            # approx pblock at optimum
            print(f"Optimal value: {obj_val}")
            #print("Blocking at optimum")
            #print(regr.predict(x[0::NVARS].reshape(1,-1))[0])


        elif self.method == "none" or self.method is None:
            x = x0 
            obj_val = obj(x)
        else:
            raise RuntimeError(f"Unknown optimization method: '{self.method}'")

        #assert(is_feasible(x))

        if EDGE_ENABLED:
            probs = {(fc[0],fc[1]): [x[NVARS*i], x[NVARS*i+1], x[NVARS*i+2], max(0.0,1.0-x[NVARS*i]-x[NVARS*i+1]-x[NVARS*i+2])]
                        for i,fc in enumerate(FC)}
        else:
            probs = {(fc[0],fc[1]): [x[NVARS*i], x[NVARS*i+1], 0, max(0.0,1.0-x[NVARS*i]-x[NVARS*i+1])]
                        for i,fc in enumerate(FC)}
        print(probs)

        
        if DUMP_SOL:
            dump_solution("nonlinear.txt", x, EDGE_ENABLED)



        # Save last computed solution
        self.last_solution = x.copy()

        return probs, obj_val


    def optimize_probabilities (self, params: OptProblemParams):
        F = params.functions
        C = params.classes

        pDeadlineL, pDeadlineC, pDeadlineE = lp_optimizer.compute_deadline_satisfaction_probs(params)


        lp_probs = None
        x0 = None
        if self.initial_guess == INITIAL_GUESS_LP or (self.initial_guess == INITIAL_GUESS_LAST_SOL and self.last_solution is None) or self.use_lp_for_bounds or self.blocking_approximation is not None:
            print("Computing initial LP sol")
            lp_probs, _ = lp_optimizer.LPOptimizer(verbose=False).optimize_probabilities(params)
        elif self.initial_guess == INITIAL_GUESS_LAST_SOL:
            x0 = self.last_solution
        elif self.initial_guess == "" or self.initial_guess is INITIAL_GUESS_NONE:
            pass
        else:
            raise RuntimeError(f"Unknown initial_guess config: '{self.initial_guess}'")

        probs, obj_val = self.optimize(params, pDeadlineL, pDeadlineC, pDeadlineE, x0, lp_probs)

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
