SEC_CONTAINER = "container"
EXPIRATION_TIMEOUT = "expiration-timeout"

SEC_SIM = "simulation"
SEED = "seed"
CLOSE_DOOR_TIME = "close-door-time"
PLOT_RESP_TIMES = "plot-rt"
STAT_PRINT_INTERVAL = "stats-print-interval"
STAT_PRINT_FILE = "stats-print-file"
MAB_STAT_PRINT_FILE = "mab-stats-print-file"
PRINT_FINAL_STATS = "print-final-stats"
SPEC_FILE = "spec-file"
EDGE_NEIGHBORS = "edge-neighbors"
EDGE_EXPOSED_FRACTION = "edge-exposed-fraction"
RESP_TIMES_FILE = "resp-times-file"
VERBOSITY = "verbosity"
RATE_UPDATE_INTERVAL = "rate-update-interval"

SEC_POLICY = "policy"
POLICY_NAME = "name"
POLICY_UPDATE_INTERVAL = "update-interval"
POLICY_ARRIVAL_RATE_ALPHA = "arrival-alpha"
ADAPTIVE_LOCAL_MEMORY = "adaptive-local-memory"
EDGE_OFFLOADING_ENABLED = "edge-offloading-enabled"
LOCAL_COLD_START_EST_STRATEGY = "local-cold-start-estimation"
CLOUD_COLD_START_EST_STRATEGY = "cloud-cold-start-estimation"
EDGE_COLD_START_EST_STRATEGY = "edge-cold-start-estimation"
HOURLY_BUDGET = "budget"
QOS_OPTIMIZER = "optimizer"
SPLIT_BUDGET_AMONG_EDGE_NODES = "split-budget-edge"
MULTIPLE_OFFLOADING_ALLOWED = "multiple-offloading-allowed"
FALLBACK_ON_LOCAL_REJECTION = "local-rejection-fallback"

SEC_STATEFUL = "stateful"

# Load Balancer
SEC_LB = "lb"
LB_POLICY = "lb-policy"

# Multi-Armed Bandit
SEC_MAB = "mab"
MAB_UPDATE_INTERVAL = "mab-update-interval"
MAB_LB_POLICIES = "mab-lb-policies"
MAB_STRATEGY = "mab-strategy"
MAB_EPSILON = "mab-epsilon"
MAB_UCB_EXPLORATION_FACTOR = "mab-ucb-exploration-factor"
MAB_RUCB_INTERVAL = "mab-rucb-interval"
MAB_SWUCB_WINDOW_SIZE = "mab-swucb-window-size"
MAB_UCB2_ALPHA = "mab-ucb2-alpha"
MAB_KL_UCB_C = "mab-kl-ucb-c"

MAB_ALL_STRATEGIES_PARAMETERS = [MAB_UCB_EXPLORATION_FACTOR, MAB_RUCB_INTERVAL, MAB_SWUCB_WINDOW_SIZE, MAB_UCB2_ALPHA, MAB_KL_UCB_C]

# stationary
MAB_REWARD_ALPHA = "mab-reward-alpha"
MAB_REWARD_BETA = "mab-reward-beta"
MAB_REWARD_GAMMA = "mab-reward-gamma"
MAB_REWARD_DELTA = "mab-reward-delta"
MAB_REWARD_ZETA = "mab-reward-zeta"

# non-stationary
MAB_NON_STATIONARY_ENABLED = "mab-non-stationary-enabled"
MAB_REWARD_ALPHA_POST = "mab-reward-alpha-post"
MAB_REWARD_BETA_POST = "mab-reward-beta-post"
MAB_REWARD_GAMMA_POST = "mab-reward-gamma-post"
MAB_REWARD_DELTA_POST = "mab-reward-delta-post"
MAB_REWARD_ZETA_POST = "mab-reward-zeta-post"


import configparser

def parse_config_file(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config
