
from utils.latency_space import GradientEstimate, NetworkCoordinateSystem, Space


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
    def __init__(self, simulation, rng):
        super().__init__(simulation, rng)
        self.space = Space(2)
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

        delta_threshold = 0.1
        for (key, list_of_npc) in keys.items():
            key_node = key_locator.get_node(key)
            key_coord = self.ncs.get_coordinates(key_node)

            # Compute step value
            step = 0.1
            for (node, node_coord, count) in list_of_npc:
                key_node_dist = self.space.distance(key_coord, node_coord)
                if key_node_dist > step:
                    step = key_node_dist
            
            delta = 1 
            candidate_node = key_node
            last_utilization = None

            while delta > delta_threshold and step > 0.00001:
                ge = GradientEstimate(self.space)
                for (node, node_coord, count) in list_of_npc:
                    # FIXME: using count instead of real datarate (the same for every pair of nodes)
                    ge.add(key_coord, node_coord, count)
                
                if not last_utilization:
                    last_utilization = ge.compute_utilization_component(key_coord, list_of_npc)
                
                next_key_coord = ge.new_point_position(key_coord, step)
                next_utilization = ge.compute_utilization_component(next_key_coord, list_of_npc)

                if next_utilization < last_utilization:
                    delta = next_utilization - last_utilization
                    last_utilization = next_utilization
                    key_coord = next_key_coord
                    candidate_node = self.ncs.get_nearest_node(next_key_coord)
                else: 
                    step = step / 2.0

            if candidate_node != key_node:
                print(f"Moving {key}: {key_node}->{candidate_node}")
                move_key(key, key_node, candidate_node)


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
