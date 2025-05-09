from abc import ABC, abstractmethod
from io import TextIOWrapper
from typing import List, Iterable
from collections import deque
import numpy as np
import math
import json
import os

# Upper bounds for the addends of the reward function
MAX_LOAD_IMBALANCE = 3  # as coefficient of variation (D^2/E), UB empirically determined
MAX_RT = 1              # max avg resp time, already normalized but can be tuned
MAX_COST = 5
MAX_UTILITY = 100000

# Abstract MAB agent
class MABAgent(ABC):
    def __init__(self, simulation, lb_policies, reward_config):

        # passo comunque un riferimento intero a Simulation
        self.simulation = simulation
        self.first_call = True

        self.lb_policies = lb_policies
        self.curr_lb_policy = None
        self.Q = np.zeros(len(lb_policies)) # reward for each policy
        self.N = np.zeros(len(lb_policies)) # number of times each policy has been chosen
        self.ALPHA = reward_config.alpha    # coefficient for load imbalance
        self.BETA  = reward_config.beta     # coefficient for response time
        self.GAMMA = reward_config.gamma    # coefficient for cost
        self.DELTA = reward_config.delta    # coefficient for utility
        self.ZETA = reward_config.zeta      # coefficient for response time violations

        # non-stationary
        self.ALPHA_POST = reward_config.alpha_post    # coefficient for load imbalance
        self.BETA_POST  = reward_config.beta_post     # coefficient for response time
        self.GAMMA_POST = reward_config.gamma_post    # coefficient for cost
        self.DELTA_POST = reward_config.delta_post    # coefficient for utility
        self.ZETA_POST = reward_config.zeta_post      # coefficient for response time violations

        if self.ALPHA + self.BETA + self.GAMMA + self.DELTA + self.ZETA != 1:
            print("[ERROR] weights of the stationary reward function do not sum to 1, please check your config file.")
            exit(1)

        if self.ALPHA_POST + self.BETA_POST+ self.GAMMA_POST + self.DELTA_POST + self.ZETA_POST != 1:
            print("[ERROR] weights of the non-stationary reward function do not sum to 1, please check your config file.")
            exit(1)

        # for non-contextual MABs that are agents for a superior RTK-MAB agent
        self.super_rtk_mab = None

        # additional data that maybe you would like to add to the MAB-stats (not mandatory, ignored if None)
        self.additional_data_output = None

    @abstractmethod
    def update_model(self, lb_policy: str, mab_stats_file: str, last_update=False):
        pass

    @abstractmethod
    def select_policy(self) -> str:
        pass

    @abstractmethod
    def _raccogli_stats(self) -> dict:
        pass

    def set_additional_data_output(self, dict):
        self.additional_data_output = dict

    def _is_mabfile_already_started(self):
        ret = False
        if self.super_rtk_mab is None: return ret
        for a in self.super_rtk_mab.agents.values():
            if a.first_call is False:
                ret = True
                break
        return ret

    def _print_stats(self, reward, mab_stats_file: TextIOWrapper, end):
        file_name = mab_stats_file.name  # ["name"]
        if self.first_call and not self._is_mabfile_already_started():
            if os.path.exists(file_name):
                os.remove(file_name)
        with open(file_name, "a") as file:
            if self.first_call:
                if not self._is_mabfile_already_started():
                    file.write("[\n")
                self.first_call = False

            data = self._raccogli_stats(reward, mab_stats_file, end)
            if self.additional_data_output is not None:
                for k, v in self.additional_data_output.items():
                    data[k] = v

            json.dump(data, file, indent=4)
            if end:
                file.write("\n]")
            else:
                file.write(",\n")


# Abstract Non-contextual MAB agent
# (see package "contextual" for contextual MABs)
class NonContextualMABAgent(MABAgent):
    def __init__(self, simulation, lb_policies: List[str], reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.reward_config = reward_config
        print("[MAB]: init Q -> ", self.Q)
        print("[MAB]: init N -> ", self.N)

    def _compute_reward(self):
        return self.ALPHA*self._compute_load_imbalance() \
            + self.BETA*self._compute_response_time() \
            + self.GAMMA*self._compute_cost() \
            + self.DELTA*self._compute_utility() \
            + self.ZETA*self._compute_rt_violations()

    def _compute_load_imbalance(self):
        server_loads = self._get_server_loads()
        mean_load = np.mean(server_loads)
        if mean_load == 0:
            return 0
        std_deviation = np.std(server_loads)
        imbalance_percentage = std_deviation / mean_load
        if imbalance_percentage/MAX_LOAD_IMBALANCE>1:
            print("[MAB] imbalance percentage out of [0, 1] bounds! ->", imbalance_percentage)
        return -(imbalance_percentage / MAX_LOAD_IMBALANCE)

    def _compute_response_time(self):
        total_resp_time_sum = sum(self.simulation.stats.resp_time_sum.values()) - sum(self.simulation.stats.ss_resp_time_sum.values())
        total_completions = sum(self.simulation.stats.completions.values()) - sum(self.simulation.stats.ss_completions.values())
        if total_completions == 0:
            return 0
        avg_rt = total_resp_time_sum / total_completions
        if avg_rt/MAX_RT>1:
            print("[MAB] average RT out of [0, 1] bounds! ->", avg_rt/MAX_RT)
        return -(avg_rt/MAX_RT)

    def _compute_cost(self):
        curr_cost = self.simulation.stats.cost - self.simulation.stats.ss_cost
        if curr_cost/MAX_COST>1:
            print("[MAB] cost out of [0, 1] bounds! ->", curr_cost/MAX_COST)
        return -(curr_cost/MAX_COST)

    def _compute_utility(self):
        curr_utility = self.simulation.stats.utility - self.simulation.stats.ss_utility
        if curr_utility/MAX_UTILITY>1:
            print("[MAB] utility out of [0, 1] bounds! ->", curr_utility/MAX_UTILITY)
        return -(1 - (curr_utility/MAX_UTILITY))

    def _compute_rt_violations(self):
        violations = sum(self.simulation.stats.violations.values()) - sum(self.simulation.stats.ss_violations.values())
        completions = sum(self.simulation.stats.completions.values()) - sum(
            self.simulation.stats.ss_completions.values())
        if completions==0: completions=1
        violations_perc = violations / completions

        if violations_perc > 1:
            print("[MAB] violations out of [0, 1] bounds! ->", violations_perc)
        return -violations_perc

    def _axis(self) -> str:
        if self.ALPHA==1: return "load_imb"
        if self.BETA==1: return "rt"
        if self.GAMMA==1: return "cost"
        if self.DELTA==1: return "utility"
        if self.ZETA==1: return "violations"
        return "NA"

    def _raccogli_stats(self, reward, mab_stats_file: TextIOWrapper, end):

            data = {}
            data["time"] = self.simulation.t
            data["policy"] = self.curr_lb_policy
            data["server_loads"] = self._get_server_loads()
            data["server_loads_cum"] = self._get_server_loads_cum()
            data["dropped_reqs"] = self._get_dropped_reqs()
            total_resp_time_sum = sum(self.simulation.stats.resp_time_sum.values()) - sum(self.simulation.stats.ss_resp_time_sum.values())
            total_completions = sum(self.simulation.stats.completions.values()) - sum(self.simulation.stats.ss_completions.values())
            if total_completions == 0:
                data["avg_resp_time"] = 0
            else:
                data["avg_resp_time"] = total_resp_time_sum / total_completions
            data["cost"] = self.simulation.stats.cost - self.simulation.stats.ss_cost
            data["utility"] = self.simulation.stats.utility - self.simulation.stats.ss_utility
            data["reward"] = reward
            return data

    def _get_server_loads(self):
        sum_server_loads1 = {}
        sum_server_loads2 = {}

        for key, value in self.simulation.stats.ss_cloud_arrivals.items():
            node = key[-1]
            sum_server_loads1[node] = sum_server_loads1.get(node, 0) + value

        for key, value in self.simulation.stats.cloud_arrivals.items():
            node = key[-1]
            sum_server_loads2[node] = sum_server_loads2.get(node, 0) + value

        result = {}
        for node in sum_server_loads1:
            result[node] = sum_server_loads2[node] - sum_server_loads1[node]

        return list(result.values())

    def _get_server_loads_cum(self):
        sum_server_loads = {}
        for key, value in self.simulation.stats.cloud_arrivals.items():
            node = key[-1]
            sum_server_loads[node] = sum_server_loads.get(node, 0) + value
        return list(sum_server_loads.values())

    def _get_dropped_reqs(self):
        dropped_reqs_1 = {}
        dropped_reqs_2 = {}

        for key, value in self.simulation.stats.ss_dropped_reqs.items():
            node = key[-1]
            dropped_reqs_1[node] = dropped_reqs_1.get(node, 0) + value

        for key, value in self.simulation.stats.dropped_reqs.items():
            node = key[-1]
            dropped_reqs_2[node] = dropped_reqs_2.get(node, 0) + value

        result = {}
        for node in dropped_reqs_1:
            result[node] = dropped_reqs_2[node] - dropped_reqs_1[node]

        return list(result.values())

# Epsilon-Greedy Strategy
class EpsilonGreedy(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], epsilon: float, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.epsilon = epsilon
        self.rng = self.simulation.mab_agent_rng

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]
        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        if not last_update:
            self._print_stats(reward, mab_stats_file, end=False)
        else:
            self._print_stats(reward, mab_stats_file, end=True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        if self.rng.random() < self.epsilon:
            # Explore: choose a random load balancing policy
            selected_policy = self.rng.choice(self.lb_policies)
        else:
            # Exploit: choose the load balancing policy with highest estimate
            maxQ = np.max(self.Q)
            # If there is a tie for the highest estimate, chooses randomly among the tied policies
            best = np.where(self.Q == maxQ)[0]
            if len(best) > 1:
                selected_policy = self.lb_policies[self.rng.choice(best)]
            else:
                selected_policy = self.lb_policies[best[0]]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy


# UCB Strategy
class UCB(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], exploration_factor: float, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.exploration_factor = exploration_factor

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]
        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        if not last_update:
            self._print_stats(reward, mab_stats_file, end=False)
        else:
            self._print_stats(reward, mab_stats_file, end=True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            if self.N[policy_index] > 0:
                mean_reward = self.Q[policy_index]
                bonus = self.exploration_factor * math.sqrt((2 * math.log(total_count)) / self.N[policy_index])
                ucb_values[policy_index] = mean_reward + bonus
            else:
                ucb_values[policy_index] = float('inf') # assicura che ogni braccio venga selezionato almeno una volta
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy

# ResetUCB Strategy
class ResetUCB(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], exploration_factor: float, reset_interval: int, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.exploration_factor = exploration_factor
        self.reset_interval = reset_interval
        self.reset_counter = 0

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.reset_counter += 1
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]

        # Check if it's time to reset
        if self.reset_counter >= self.reset_interval:
            self._reset()

        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        if not last_update:
            self._print_stats(reward, mab_stats_file, end=False)
        else:
            self._print_stats(reward, mab_stats_file, end=True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            if self.N[policy_index] > 0:
                mean_reward = self.Q[policy_index]
                bonus = self.exploration_factor * math.sqrt((2 * math.log(total_count)) / self.N[policy_index])
                ucb_values[policy_index] = mean_reward + bonus
            else:
                ucb_values[policy_index] = float('inf') # assicura che ogni braccio venga selezionato almeno una volta
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy

    def _reset(self):
        self.N = np.zeros(len(self.lb_policies)) # number of times each policy has been chosen
        self.Q = np.zeros(len(self.lb_policies)) # reward for each policy
        self.reset_counter = 0

# SlidingWindowUCB Strategy
class SlidingWindowUCB(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], exploration_factor: float, window_size: int, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.exploration_factor = exploration_factor
        self.window_size = window_size
        self.history = deque(maxlen=window_size) # Finestra scorrevole

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)

        # Se la finestra scorrevole è piena, rimuovi l'elemento più vecchio
        if len(self.history) == self.window_size:
            oldest_policy, oldest_reward = self.history.popleft()
            self._decrement_counts_and_rewards(oldest_policy, oldest_reward)

        # Aggiungi la nuova entry alla finestra e aggiorna i contatori
        self.history.append((policy_index, reward))
        self._increment_counts_and_rewards(policy_index, reward)

        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        if not last_update:
            self._print_stats(reward, mab_stats_file, end=False)
        else:
            self._print_stats(reward, mab_stats_file, end=True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            if self.N[policy_index] > 0:
                mean_reward = self.Q[policy_index]
                bonus = self.exploration_factor * math.sqrt((2 * math.log(total_count)) / self.N[policy_index])
                ucb_values[policy_index] = mean_reward + bonus
            else:
                ucb_values[policy_index] = float('inf') # assicura che ogni braccio venga selezionato almeno una volta
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy

    def _increment_counts_and_rewards(self, policy_index, reward):
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]

    def _decrement_counts_and_rewards(self, policy_index, reward):
        if self.N[policy_index] > 0:
            self.N[policy_index] -= 1
            if self.N[policy_index] == 0:
                self.Q[policy_index] = 0
            else:
                self.Q[policy_index] = (self.Q[policy_index] * self.N[policy_index] - reward) / self.N[policy_index]


# UCB2 Strategy
class UCB2(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], exploration_factor: float, reward_config, alpha: float):
        super().__init__(simulation, lb_policies, reward_config)
        self.exploration_factor = exploration_factor
        if alpha<=0 or alpha>=1:
            print("[ERROR] UCB2 \"alpha\" parameter must be into (0, 1),", alpha, "received instead.")
            exit(1)
        self.alpha = alpha
        self.R = np.zeros(len(lb_policies))  # number of times each policy has been chosen
        self.remaining_locked_plays = 0  # number of arm selection locked by the most promising arm selected in previous epochs

        print("[MAB]: init R -> ", self.R)

    def __tau(self, r):
        return math.ceil(math.pow(1 + self.alpha, r))

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]

        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        print("[MAB]: R updated -> ", self.R)
        if not last_update:
            self._print_stats(reward, mab_stats_file, False)
        else:
            self._print_stats(reward, mab_stats_file, True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        # init: in the first execution, play each arm once
        #       without any further computation
        for index, label in enumerate(self.lb_policies):
            if self.N[index] == 0:
                print("[MAB] INIT: selecting", label, "(", index, ") for the first time")
                return self.lb_policies[index]

        # if a specific arm was previously selected,
        # continue executing it for the remaining f(\tau(R)) times (see below)
        if self.remaining_locked_plays > 0:
            self.remaining_locked_plays -= 1
            print("[MAB] Policy selection locked by UCB2 on", self.curr_lb_policy, ",", self.remaining_locked_plays,
                  "plays remaining.")
            return None

        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            mean_reward = self.Q[policy_index]
            tau_r = self.__tau(self.R[policy_index])
            bonus = (self.exploration_factor * math.sqrt(
                ((1 + self.alpha) * math.log(math.e * total_count / tau_r)) / (2 * tau_r)))
            ucb_values[policy_index] = mean_reward + bonus
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        selected_index = self.lb_policies.index(selected_policy)

        # once the arm is selected, "lock" it for f(\tau(R)) subsequent plays:
        tau_r_selected = self.__tau(self.R[selected_index])
        tau_r1_selected = self.__tau(self.R[selected_index] + 1)

        if tau_r1_selected - tau_r_selected < 0:
            print("[MAB] ERROR: negative remaining_locked_plays =", self.remaining_locked_plays)
            exit(1)

        # \tau differences could be zero, set a minimum of 1 execution
        self.remaining_locked_plays = max(1, tau_r1_selected - tau_r_selected)

        self.remaining_locked_plays -= 1  # because decrementing is done while selecting the policy, i.e. here
        self.R[selected_index] += 1  # increment the epoch counter
        print("[MAB] Starting epoch no.", int(self.R[selected_index]), "for policy", selected_policy, "(",
              selected_index,
              ") - it will last for", self.remaining_locked_plays + 1, "subsequent plays.")

        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy

# UCB-tuned Strategy
class UCBTuned(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], exploration_factor: float, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.exploration_factor = exploration_factor
        self.M2 = np.zeros(len(lb_policies))    # sum of squared deviations, for variance computation

    def __compute_v(self, index: int):
        s = self.N[index]
        t = sum(self.N)
        variance = self.M2[index] / s
        return variance + math.sqrt((2 * math.log(t)) / s)

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.N[policy_index] += 1
        delta = reward - self.Q[policy_index]                               # Q_(n-1)
        self.Q[policy_index] += delta / self.N[policy_index]
        self.M2[policy_index] += delta * (reward - self.Q[policy_index])    # Q_n
        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        print("[MAB]: M2 updated -> ", self.M2)
        if not last_update:
            self._print_stats(reward, mab_stats_file, False)
        else:
            self._print_stats(reward, mab_stats_file, True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            if self.N[policy_index] > 0:
                mean_reward = self.Q[policy_index]
                v = self.__compute_v(policy_index)

                bonus = (self.exploration_factor * math.sqrt(
                    (math.log(total_count) / self.N[policy_index]) * min(0.25, v)))
                ucb_values[policy_index] = mean_reward + bonus
            else:
                ucb_values[policy_index] = float('inf')  # assicura che ogni braccio venga selezionato almeno una volta
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy


# KL-UCB Strategy
class KLUCB(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], exploration_factor: float, reward_config, c: float):
        super().__init__(simulation, lb_policies, reward_config)
        self.exploration_factor = exploration_factor
        self.c = c                              # KL constant
        self.cumQ = np.zeros(len(lb_policies))  # Sum of rewards

    def __kl(self, p, q):
        if p == q:
            return 0.0
        elif q == 0 or q == 1:
            return np.inf
        return (p*math.log(p/q))+((1-p)*math.log((1-p)/(1-q)))

    def __q(self, index):
        t=sum(self.N)
        shifted_reward = self.Q[index] + 1  # in order to have the reward into [0, 1], as required by KL
        upper_limit = 1.0
        lower_limit = shifted_reward
        epsilon = 1e-6  # tolerance
        target = (np.log(t) + self.c * np.log(np.log(t))) / self.N[index]

        # find the q value via binary searhc
        while upper_limit - lower_limit > epsilon:
            q = (upper_limit + lower_limit) / 2
            if self.__kl(-(self.cumQ[index])/self.N[index], q) <= target:
                lower_limit = q
            else:
                upper_limit = q
        return (upper_limit + lower_limit) / 2

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]
        self.cumQ[policy_index]+=reward
        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        print("[MAB]: cumQ updated -> ", self.cumQ)
        if not last_update:
            self._print_stats(reward, mab_stats_file, end=False)
        else:
            self._print_stats(reward, mab_stats_file, end=True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        # init: in the first execution, play each arm once
        #       without any further computation
        #       Oss.: setting "inf" in the last loop for the initialization
        #             does not prevent q computation for the default policy,
        #             resulting in a "divide by zero" error.
        for index, label in enumerate(self.lb_policies):
            if self.N[index] == 0:
                print("[MAB] INIT: selecting", label, "(", index, ") for the first time")
                return self.lb_policies[index]

        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            ucb_values[policy_index] = self.exploration_factor * self.__q(policy_index)
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy

# KL-UCB Strategy, with single parameter
class KLUCBsp(NonContextualMABAgent):
    def __init__(self, simulation, lb_policies: List[str], reward_config, c: float):
        super().__init__(simulation, lb_policies, reward_config)
        self.c = c                              # KL constant
        self.cumQ = np.zeros(len(lb_policies))  # Sum of rewards

    def __kl(self, p, q):
        if p == q:
            return 0.0
        elif q == 0 or q == 1:
            return np.inf
        return (p*math.log(p/q))+((1-p)*math.log((1-p)/(1-q)))

    def __q(self, index):
        t=sum(self.N)
        shifted_reward = self.Q[index] + 1  # in order to have the reward into [0, 1], as required by KL
        upper_limit = 1.0
        lower_limit = shifted_reward
        epsilon = 1e-6  # tolerance
        target = (np.log(t) + self.c * np.log(np.log(t))) / self.N[index]

        # find the q value via binary searhc
        while upper_limit - lower_limit > epsilon:
            q = (upper_limit + lower_limit) / 2
            if self.__kl(-(self.cumQ[index])/self.N[index], q) <= target:
                lower_limit = q
            else:
                upper_limit = q
        return (upper_limit + lower_limit) / 2

    def update_model(self, lb_policy: str, mab_stats_file:str, last_update=False):
        self.curr_lb_policy = lb_policy
        reward = self._compute_reward()
        policy_index = self.lb_policies.index(lb_policy)
        self.N[policy_index] += 1
        self.Q[policy_index] += (reward - self.Q[policy_index]) / self.N[policy_index]
        self.cumQ[policy_index]+=reward
        print("[MAB]: Q updated -> ", self.Q)
        print("[MAB]: N updated -> ", self.N)
        print("[MAB]: cumQ updated -> ", self.cumQ)
        if not last_update:
            self._raccogli_stats(reward, mab_stats_file, end=False)
        else:
            self._raccogli_stats(reward, mab_stats_file, end=True)
        self.simulation.stats.do_snapshot()

    def select_policy(self) -> str:
        # init: in the first execution, play each arm once
        #       without any further computation
        #       Oss.: setting "inf" in the last loop for the initialization
        #             does not prevent q computation for the default policy,
        #             resulting in a "divide by zero" error.
        for index, label in enumerate(self.lb_policies):
            if self.N[index] == 0:
                print("[MAB] INIT: selecting", label, "(", index, ") for the first time")
                return self.lb_policies[index]

        total_count = sum(self.N)
        ucb_values = [0.0 for _ in self.lb_policies]
        for p in self.lb_policies:
            policy_index = self.lb_policies.index(p)
            ucb_values[policy_index] = self.__q(policy_index)
        selected_policy = self.lb_policies[ucb_values.index(max(ucb_values))]
        if self.curr_lb_policy == selected_policy:
            return None
        return selected_policy
