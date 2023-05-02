EXP_TAG="edge_memory_1shot"

import main
import conf
import json
import pandas as pd

STATS_FILE="/tmp/stats.txt"

config = main.parse_config_file()
config.set(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, "5000")
config.set(conf.SEC_SIM, conf.STAT_PRINT_FILE, STATS_FILE)
config.set(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, "10000")
config.set(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, "5000")
config.set(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA, "1.0")

POLICIES = ["probabilistic", "probabilistic-legacy", "basic"]
MEMORY = [512*i for i in [1,2,4,8,12,19,24,32]]
SEEDS = [1,2,53,12,567]

results = []
COL_NAMES = ["Policy", "Memory", "Seeds", "Utility", "Cost"]

results = []

for policy in POLICIES:
    config.set(conf.SEC_POLICY, conf.POLICY_NAME, policy)
    for mem in MEMORY:
        config.set("edge", "memory", str(mem))
        for s1 in SEEDS:
            config.set(conf.SEC_SIM, conf.SEED, str(s1))
            simulation = main.init_simulation(config)
            simulation.run()

            # Compute utility and cost difference before and after policy update
            with open(STATS_FILE, "r") as jsonf:
                stats = json.load(jsonf)
                stats = sorted(stats, key=lambda x: x["_Time"])
                assert(len(stats)==2)
                utility = stats[1]["utility"]-stats[0]["utility"]
                cost = stats[1]["cost"]-stats[0]["cost"]
                results.append((policy,mem,s1,,utility, cost))


df = pd.DataFrame(results, columns=COL_NAMES)
mean_df = df.groupby(["Policy", "Memory"]).mean()
std_df = df.groupby(["Policy", "Memory"]).std()
merged = pd.merge(mean_df, std_df, on=["Policy", "Memory"], suffixes=["Mean","Std"])

print(merged)
merged.to_csv(f"results/results_{EXP_TAG}.csv")

with open(f'results/conf_{EXP_TAG}.ini', 'w') as configfile:
    config.write(configfile)
