
from utils.latency_space import GradientEstimate, NetworkCoordinateSystem, Point, Space, SpringForce
from optimizer import solve

class KeyLocator:
    
    def __init__ (self):
        self.mapping = {}

    def update_key_location (self, key, node):
        self.mapping[key] = node

    def get_node (self, key):
        return self.mapping[key]

def init_key_placement (functions, infra, rng):
    # Place all the keys in the cloud
    cloud_node = infra.get_cloud_nodes()[0]
    for f in functions:
        for k,_ in f.accessed_keys:
            if not k in cloud_node.kv_store:
                size = rng.uniform(10, 1000000) # TODO
                cloud_node.kv_store[k] = size
                key_locator.update_key_location(k, cloud_node)
                print(f"Placed {k} in {cloud_node}")

def move_key (k, src_node, dest_node):
    if src_node == dest_node:
        return
    dest_node.kv_store[k] = src_node.kv_store[k]
    del(src_node.kv_store[k])
    key_locator.update_key_location(k, dest_node)

key_locator = KeyLocator()

# ---------------------------------------------------


class KeyMigrationPolicy():

    def __init__ (self, simulation, rng):
        self.simulation = simulation
        self.rng = rng
        self.rate_update_alpha = 0.33
        self.__last_update = 0

        self.arrival_rates = {}
        self.__last_arrivals = None

        self.data_access_rates = {}
        self.__last_data_access = None

        self.all_keys = set()
        for f in simulation.functions:
            for k,_ in f.accessed_keys:
                self.all_keys.add(k)

    def migrate(self):
        pass

    def update_metrics (self):
        stats = self.simulation.stats

        # Estimate arrival rates based on arrival count
        if self.__last_arrivals is not None:
            arrival_rates = {}
            for f in self.simulation.functions:
                for n in self.simulation.infra.get_nodes():
                    new_arrivals = 0
                    for c in self.simulation.classes:
                        new_arrivals += stats.arrivals[(f, c, n)] - self.__last_arrivals[(f, c, n)]
                    new_rate = new_arrivals / (self.simulation.t - self.__last_update)
                    self.arrival_rates[(f, n)] = self.rate_update_alpha * new_rate + \
                                             (1.0 - self.rate_update_alpha) * self.arrival_rates[(f, n)]
        else:
            for f in self.simulation.functions:
                for n in self.simulation.infra.get_nodes():
                    arrivals = 0
                    for c in self.simulation.classes:
                        arrivals += stats.arrivals[(f, c, n)]
                    self.arrival_rates[(f, n)] = arrivals / self.simulation.t

        # Estimate data access rates based on data access count
        if self.__last_data_access is not None:
            data_access_rates = {}
            for k in self.all_keys:
                for f in self.simulation.functions:
                    for n in self.simulation.infra.get_nodes():
                        new_arrivals = stats.data_access_count[(k, f, n)] - self.__last_data_access[(k, f, n)]
                        new_rate = new_arrivals / (self.simulation.t - self.__last_update)
                        self.data_access_rates[(k, f, n)] = self.rate_update_alpha * new_rate + \
                                                (1.0 - self.rate_update_alpha) * self.data_access_rates[(k, f, n)]
        else:
            for k in self.all_keys:
                for f in self.simulation.functions:
                    for n in self.simulation.infra.get_nodes():
                        arrivals = stats.data_access_count[(k, f, n)]
                        self.data_access_rates[(k, f, n)] = arrivals / self.simulation.t

        print(self.data_access_rates) # TODO

        self.__last_arrivals = stats.arrivals.copy()
        self.__last_data_access = stats.data_access_count.copy()
        self.__last_update = self.simulation.t



class RandomKeyMigrationPolicy(KeyMigrationPolicy):

    def __init__ (self, simulation, rng):
        super().__init__(simulation, rng)

    def migrate(self):
        # Move keys randomly
        nodes = self.simulation.infra.get_nodes()
        for n in nodes:
            keys = list(n.kv_store.keys())
            for key in keys:
                dest = self.rng.choice(nodes)
                print(f"Moving {key} {n}->{dest}")
                move_key(key, n, dest)


class GradientBasedMigrationPolicy(KeyMigrationPolicy):
    '''
        GradientBasedMigrationPolicy implements the placement algorithm described in: 
            Rizou et al., "Solving the multi-operator placement problem in large-scale 
            operator networks.", ICCCN'10. 
    '''
    utilization_delta_threshold = 0.1
    min_gradient_update_step = 0.00001
    
    def __init__(self, simulation, rng):
        super().__init__(simulation, rng)
        self.space = Space(3)
        self.ncs = NetworkCoordinateSystem(self.simulation.infra, self.space, self.rng)

    def migrate(self):
        keys = {} 
        for ((key, _, node), count) in self.data_access_rates.items():
            if count == 0:
                continue
            key_node = key_locator.get_node(key)
            node_coord = self.ncs.get_coordinates(node)
            if key not in keys:
                keys[key] = [(node, node_coord, count)]
            else:
                keys[key].append((node, node_coord, count))

        for (key, list_of_npc) in keys.items():
            key_node = key_locator.get_node(key)
            key_coord = self.ncs.get_coordinates(key_node)

            # Compute step value (alg. 2, line 3)
            step = GradientBasedMigrationPolicy.min_gradient_update_step
            for (node, node_coord, count) in list_of_npc:
                key_node_dist = self.space.distance(key_coord, node_coord)
                if key_node_dist > step:
                    step = key_node_dist
            
            delta = GradientBasedMigrationPolicy.utilization_delta_threshold + 1 
            candidate_node = key_node
            last_utilization = None

            while delta > GradientBasedMigrationPolicy.utilization_delta_threshold and step > GradientBasedMigrationPolicy.min_gradient_update_step:
                # Compute gradient of network usage (alg 2, line 5)
                ge = GradientEstimate(self.space)
                for (node, node_coord, count) in list_of_npc:
                    # Note: we are using count instead of the exchanged datarate 
                    # (this should be count * key_value_size, but we avoid unneeded computation)
                    ge.add(key_coord, node_coord, count)
                
                if not last_utilization:
                    last_utilization = ge.compute_utilization_component(key_coord, list_of_npc)
                
                # Check if key migration improves network usage (line 6)
                next_key_coord = ge.new_point_position(key_coord, step)
                next_utilization = ge.compute_utilization_component(next_key_coord, list_of_npc)
                if next_utilization < last_utilization:
                    delta = next_utilization - last_utilization
                    last_utilization = next_utilization
                    key_coord = next_key_coord
                    candidate_node = self.ncs.get_nearest_node(next_key_coord)
                else: 
                    step = step / 2.0

            if candidate_node != None and candidate_node != key_node:
                print(f"Moving {key}: {key_node}->{candidate_node}")
                move_key(key, key_node, candidate_node)


class SpringBasedMigrationPolicy(KeyMigrationPolicy):
    '''
        SpringBasedMigrationPolicy implements the placement algorithm described in: 
            Pietzuch et al., "Network-Aware Operator Placement for Stream-Processing 
            Systems.", ICDE'06. 
    '''
    force_threshold = 1     # value used in the authors' paper
    delta = 0.1             # value used in the authors' paper

    def __init__(self, simulation, rng):
        super().__init__(simulation, rng)
        self.space = Space(3)
        self.ncs = NetworkCoordinateSystem(self.simulation.infra, self.space, self.rng)

    def migrate(self):
        keys = {} 
        for ((key, _, node), count) in self.data_access_rates.items():
            if count == 0:
                continue
            key_node = key_locator.get_node(key)
            node_coord = self.ncs.get_coordinates(node)
            if key not in keys:
                keys[key] = [(node, node_coord, count)]
            else:
                keys[key].append((node, node_coord, count))

        for (key, list_of_npc) in keys.items():
            key_node = key_locator.get_node(key)
            key_coord = self.ncs.get_coordinates(key_node)
            _key_coord = Point(key_coord.coordinates.copy())

            force_abs = SpringBasedMigrationPolicy.force_threshold + 1 
            candidate_node = key_node
            guard = 10000
            while force_abs > SpringBasedMigrationPolicy.force_threshold and guard > 0:
                guard -= 1
                # Compute gradient of network usage (alg 2, line 5)
                f = SpringForce(self.space)
                for (node, node_coord, count) in list_of_npc:
                    # Note: we are using count instead of the exchanged datarate 
                    # (this should be count * key_value_size, but we avoid unneeded computation)
                    f.add(_key_coord, node_coord, count)
                _key_coord = f.move_point(_key_coord, SpringBasedMigrationPolicy.delta)
                force_abs = f.magnitude()
            
            candidate_node = self.ncs.get_nearest_node(_key_coord)

            if candidate_node != None and candidate_node != key_node:
                print(f"Moving {key}: {key_node}->{candidate_node}")
                move_key(key, key_node, candidate_node)

class SimpleGreedyMigrationPolicy(KeyMigrationPolicy):
    '''
        Always move key to functions with higher count * latency value, 
        aiming to reduce latency of the most active function for each 
        key.
    '''
    def __init__(self, simulation, rng):
        super().__init__(simulation, rng)

    def migrate(self):
        keys = {} 
        for ((key, _, node), count) in self.data_access_rates.items():
            if count == 0:
                continue
            if key not in keys:
                keys[key] = [(node, count)]
            else:
                keys[key].append((node, count))

        for (key, list_of_nc) in keys.items():
            key_node = key_locator.get_node(key)
            scores = []

            for (node, count) in list_of_nc:
                node_score = self.simulation.infra.get_latency(key_node, node)
                node_score = node_score * count
                scores.append((node, node_score))
            scores = sorted(scores, reverse=True, key = lambda x: x[1])
            best_node = scores[0][0]

            if best_node != None and best_node != key_node:
                print(f"Moving {key}: {key_node}->{best_node}")
                move_key(key, key_node, best_node)

class ILPBasedMigrationPolicy(KeyMigrationPolicy):
    '''
        TODO
    '''
    def __init__(self, simulation, rng):
        super().__init__(simulation, rng)

    def __solve_opt_problem(self, keys): 
        import pulp as pl

        # TODO: where to place these weights? 
        W_ACCESS = 0.5
        W_MIGRATION = 0.5

        VERBOSE = self.simulation.verbosity
        nodes = self.simulation.infra.get_nodes()

        # Problem (minimization)
        prob = pl.LpProblem("MigrationProblem", pl.LpMinimize)
        # Placement
        x = pl.LpVariable.dicts("x", (keys, nodes), 0, None, pl.LpBinary)
        # Migration
        y = pl.LpVariable.dicts("y", (keys, nodes, nodes), 0, None, pl.LpBinary)

        # Defining the average time f on i spend to access k on j
        t_data_fi_kjs = {}
        t_data_k_max = {}
        for (key, list_of_nfr) in keys.items():
            key_node = key_locator.get_node(key)
            value_size = key_node.kv_store[key]
            t_data_k_max[key] = 0
            for (i_node, f, access_rate) in list_of_nfr:
                for j_node in nodes: 
                    d_ij = self.simulation.infra.get_latency(i_node, j_node)
                    bw_ij = self.simulation.infra.get_bandwidth(i_node, j_node)
                    # TODO: use probability not directly the access rate
                    t_data_fi_kjs[(key, j_node)] = access_rate * (2 * d_ij + value_size / bw_ij)
                    if t_data_fi_kjs[(key, j_node)] > t_data_k_max[key]:
                        t_data_k_max[key] = t_data_fi_kjs[(key, j_node)]

        # Defining the key k migration time from i to j
        t_migr_kijs = {}
        t_migr_k_max = {}
        for (key, list_of_nfr) in keys.items():
            key_node = key_locator.get_node(key)
            value_size = key_node.kv_store[key]
            t_migr_k_max[key] = 0
            for i_node in nodes: 
                for j_node in nodes: 
                    if i_node == j_node:
                        t_migr_kijs[(key, i_node, j_node)] = 0
                    else:
                        d_ij = self.simulation.infra.get_latency(i_node, j_node)
                        bw_ij = self.simulation.infra.get_bandwidth(i_node, j_node)
                        t_migr_kijs[(key, i_node, j_node)] = (2 * d_ij + value_size / bw_ij)
                        if t_migr_kijs[(key, i_node, j_node)] > t_migr_k_max[key]:
                            t_migr_k_max[key] = t_migr_kijs[(key, i_node, j_node)]
        
        # Objective function (minimization problem)
        prob += W_ACCESS * pl.lpSum([x[k][j] * t_data_fi_kjs[(k,j)] / t_data_k_max[k] for j in nodes for k in keys]) + \
            W_MIGRATION * pl.lpSum([y[k][i][j] * t_migr_kijs[(k,i,j)] / t_migr_k_max[k] for i in nodes for j in nodes for k in keys]), \
            "Min avg t_access and t_migr"
        
        # Defining symbols x_bar representing the previous allocation 
        x_bar_kis = {}
        for (k, list_of_nfr) in keys.items():
            node = key_locator.mapping[k]
            for i in nodes: 
                x_bar_kis[(k,i)] = 1 if i == node else 0

        # Collecting value size for each key
        l_ks = {}
        for key in keys:
            # TODO: check unit of size in kv_store
            l_k = key_locator.get_node(key).kv_store[key] / 1024 
            l_ks[key] = l_k

        # Adding constraints: define y_k,i,j
        for (k, _) in keys.items():
            for i in nodes: 
                for j in nodes: 
                    prob += y[k][i][j] <= x_bar_kis[(k,i)], f"eq_6__{i},{j}"
                    prob += y[k][i][j] <= x[k][j], f"eq_7__{i},{j}"
                    prob += y[k][i][j] >= (x_bar_kis[(k,i)] + x[k][j] - 1), f"eq_8__{i},{j}"

        # Adding constraints: available memory to allocate k on j 
        for j in nodes: 
            prob += pl.lpSum([l_ks[k] * x[k][j] for k in keys]) <= j.curr_memory, f"eq_9__{j}"
        
        # Adding constraints: select a single node to host k 
        for k in keys: 
            prob += pl.lpSum([x[k][j] for j in nodes]) == 1, f"eq_10__{f}"
        
        # Solving the problem 
        if VERBOSE:
            prob.writeLP("/tmp/problem.lp")
        status = solve(prob)
        obj = pl.value(prob.objective)

        # TODO: review logging messages
        if VERBOSE:
            print(f" Problem solved. {status} solution found.")
            print(f" > objective function: {obj}")
        if obj is None:
            print(f"WARNING: objective is None")
            return None

        # Exporting results
        allocation = { }
        # migration =  { }
        for k in keys: 
            for j in nodes: 
                if pl.value(x[k][j]) == 1.0:
                    allocation[k] = j
                # for i in nodes: 
                #     if pl.value(y[k][i][j]) == 1.0:
                #         migration[(k,i)] = j 

        return allocation 

    def migrate(self):
        keys = {} 
        for ((key, func, node), access_rate) in self.data_access_rates.items():
            if access_rate == 0:
                continue
            if key not in keys:
                keys[key] = [(node, func, access_rate)]
            else:
                keys[key].append((node, func, access_rate))

        key2node = self.__solve_opt_problem(keys)
        for key in keys:
            key_node = key_locator.get_node(key)
            best_node = key2node[key]

            if best_node != None and best_node != key_node:
                print(f"Moving {key}: {key_node}->{best_node}")
                move_key(key, key_node, best_node)
        

# -------------------------------------------------------------------------
import policy as offloading_policy

class AlwaysOffloadStatefulPolicy(offloading_policy.Policy):

    def __init__(self, simulation, node):
        super().__init__(simulation, node)

    def schedule(self, f, c, offloaded_from):
        if len(offloaded_from) > 2:
            if self.can_execute_locally(f):
                return offloading_policy.SchedulerDecision.EXEC, None
            else:
                return offloading_policy.SchedulerDecision.DROP, None

        remote_nodes = {}
        # Add all the nodes storing keys for the function
        for k,p in f.accessed_keys:
            key_node = key_locator.get_node(k)
            value_size = key_node.kv_store[k]
            remote_nodes[key_node] = remote_nodes.get(key_node,0) + p*value_size

        # pick node with maximum expected data to retrieve
        sorted_nodes = sorted(remote_nodes.items(), key=lambda x: x[1], reverse=True)
        best_node = sorted_nodes[0][0]

        if best_node == self.node and not self.can_execute_locally(f):
            if len(sorted_nodes > 1):
                best_node = sorted_nodes[1][0]
            else:
                return offloading_policy.SchedulerDecision.DROP, None
        elif best_node == self.node:
            return offloading_policy.SchedulerDecision.EXEC, None

        
        return (offloading_policy.SchedulerDecision.OFFLOAD_EDGE, best_node)

class StateAwareOffloadingPolicy(offloading_policy.GreedyPolicy):

    def __init__(self, simulation, node):
        super().__init__(simulation, node)
        self.latency_estimation_cache = {}

    def schedule(self, f, c, offloaded_from):
        remote_nodes = set([self.cloud])
        # Add all the nodes storing keys for the function
        for k,_ in f.accessed_keys:
            remote_nodes.add(key_locator.get_node(k))

        # XXX: We do not consider cold start here

        if not self.can_execute_locally(f):
            exp_latency_local = float("inf")
        else:
            duration = f.serviceMean/self.node.speedup
            exp_latency_local = duration 

            for k,p in f.accessed_keys:
                if not k in self.node.kv_store:
                    key_node = key_locator.get_node(k)
                    value_size = key_node.kv_store[k]
                    extra_latency = self.simulation.infra.get_latency(self.node, key_node)*2 +\
                           value_size/(self.simulation.infra.get_bandwidth(self.node, key_node)*125000)
                    exp_latency_local += p*extra_latency
        
        if len(offloaded_from) > 2:
            if self.can_execute_locally(f):
                return offloading_policy.SchedulerDecision.EXEC, None
            else:
                return offloading_policy.SchedulerDecision.DROP, None

        if f in self.latency_estimation_cache:
            best_node, best_lat = self.latency_estimation_cache[f]
        else:
            exp_latency = {}
            for remote_node in remote_nodes:
                rtt = 2*self.simulation.infra.get_latency(self.node, remote_node)
                bw = self.simulation.infra.get_bandwidth(self.node, remote_node)
                duration = f.serviceMean/remote_node.speedup
                # Offloading time:
                l = duration + rtt + f.inputSizeMean*8/1000/1000/bw
                # Key access time:
                for k,p in f.accessed_keys:
                    if not k in remote_node.kv_store:
                        key_node = key_locator.get_node(k)
                        value_size = key_node.kv_store[k]
                        extra_latency = self.simulation.infra.get_latency(remote_node, key_node)*2 +\
                            value_size/(self.simulation.infra.get_bandwidth(remote_node, key_node)*125000)
                        l += p*extra_latency
                exp_latency[remote_node] = l

            best_node, best_lat = sorted(exp_latency.items(), key=lambda x: x[1])[0]
            self.latency_estimation_cache[f] = (best_node, best_lat)

        if exp_latency_local < best_lat:
            return offloading_policy.SchedulerDecision.EXEC, None
        else:
            return (offloading_policy.SchedulerDecision.OFFLOAD_EDGE, best_node)
