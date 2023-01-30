EXP_TAG="policies"

import pandas as pd
import main
import conf

config = main.parse_config_file()
config.set(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, "-1")

#POLICIES = ["probabilistic", "probabilistic-legacy", "greedy", "greedy-min-cost", "basic", "random"]
POLICIES = ["probabilistic", "greedy", "greedy-min-cost", "basic", "random"]
#POLICIES = ["greedy", "basic", "random"]
SEEDS = [(1,56), (2,23), (53, 98), (12,90), (567, 4)]
#SEEDS = [(1,56)]

results = []
COL_NAMES = ["Policy", "Seeds", "Utility", "Cost"]


for policy in POLICIES:
    config.set(conf.SEC_POLICY, conf.POLICY_NAME, policy)
    for s1,s2 in SEEDS:
        config.set(conf.SEC_SEED, conf.SEED_ARRIVAL, str(s1))
        config.set(conf.SEC_SEED, conf.SEED_SERVICE, str(s2))
        simulation = main.init_simulation(config)
        stats = simulation.run()

        results.append((policy,(s1,s2),stats.utility, stats.cost))

df = pd.DataFrame(results, columns=COL_NAMES)
mean_df = df.groupby("Policy").mean()
std_df = df.groupby("Policy").std()
merged = pd.merge(mean_df, std_df, on="Policy", suffixes=["Mean","Std"])

print(merged)
merged.to_csv(f"results/results_{EXP_TAG}.csv")

with open(f'results/conf_{EXP_TAG}.ini', 'w') as configfile:
    config.write(configfile)
