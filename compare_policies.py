import main
import conf

config = main.parse_config_file()

stats = {}
POLICIES = ["probabilistic", "basic", "random"]

for policy in POLICIES:
    config.set(conf.SEC_POLICY, conf.POLICY_NAME, policy)
    simulation = main.init_simulation(config)
    stats[policy] = simulation.run()

for policy in POLICIES:
    s = stats[policy]
    print(f"{policy}: {s.utility}")
