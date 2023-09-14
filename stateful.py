
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
        self.__last_arrivals = None
        self.__last_update = 0
        self.arrival_rates = {}
        self.arrival_rate_alpha = 0.33

    def migrate(self):
        pass

    def update_metrics (self):
        stats = self.simulation.stats

        if self.__last_arrivals is not None:
            arrival_rates = {}
            for f in self.simulation.functions:
                for n in self.simulation.infra.get_nodes():
                    new_arrivals = 0
                    for c in self.simulation.classes:
                        new_arrivals += stats.arrivals[(f, c, n)] - self.__last_arrivals[(f, c, n)]
                    new_rate = new_arrivals / (self.simulation.t - self.__last_update)
                    self.arrival_rates[(f, n)] = self.arrival_rate_alpha * new_rate + \
                                             (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, n)]
        else:
            for f in self.simulation.functions:
                for n in self.simulation.infra.get_nodes():
                    arrivals = 0
                    for c in self.simulation.classes:
                        arrivals += stats.arrivals[(f, c, n)]
                    self.arrival_rates[(f, n)] = arrivals / self.simulation.t
        print(self.arrival_rates)

        self.__last_arrivals = stats.arrivals.copy()
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


    

# -------------------------------------------------------------------------
import policy as offloading_policy

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
