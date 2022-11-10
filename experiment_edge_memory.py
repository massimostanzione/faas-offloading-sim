EXP_TAG="edge_memory"

import main
import conf
import pandas as pd

config = main.parse_config_file()
config.set(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, "-1")

POLICIES = ["probabilistic", "probabilistic-legacy", "basic"]
MEMORY = [512*i for i in [1,2,4,8,12,19,24,32]]
SEEDS = [(1,56), (2,23), (53, 98), (12,90), (567, 4)]

results = []
COL_NAMES = ["Policy", "Memory", "Seeds", "Utility", "Cost"]

results = []

for policy in POLICIES:
    config.set(conf.SEC_POLICY, conf.POLICY_NAME, policy)
    for mem in MEMORY:
        config.set("edge", "memory", str(mem))
        for s1,s2 in SEEDS:
            config.set(conf.SEC_SEED, conf.SEED_ARRIVAL, str(s1))
            config.set(conf.SEC_SEED, conf.SEED_SERVICE, str(s2))
            simulation = main.init_simulation(config)
            stats = simulation.run()
            results.append((policy,mem,(s1,s2),stats.utility, stats.cost))


df = pd.DataFrame(results, columns=COL_NAMES)
mean_df = df.groupby(["Policy", "Memory"]).mean()
std_df = df.groupby(["Policy", "Memory"]).std()
merged = pd.merge(mean_df, std_df, on=["Policy", "Memory"], suffixes=["Mean","Std"])

print(merged)
merged.to_csv(f"results/results_{EXP_TAG}.csv")

with open(f'results/conf_{EXP_TAG}.ini', 'w') as configfile:
    config.write(configfile)
