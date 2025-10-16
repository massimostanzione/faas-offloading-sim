def compute_stability_index(instance_result_record: dict, strategy: str):
    invoks = len(instance_result_record["policy"])
    expl = 0
    # UCB strategy was implemented before event registry,
    # so it needs a specific mechanism to compute initializations and invocations
    if strategy == "UCB":
        inits = 7
        for i in range(7, len(instance_result_record["policy"]) - 1):
            if instance_result_record["policy"][i] != instance_result_record["policy"][i + 1]:
                expl += 1

    else:
        inits = 0

        for event_group in instance_result_record["mab-occurred-events"]:
            for event in event_group:
                if event["event_type"] == "INITIALIZATION" and strategy != "UCB":
                    inits += 1
                elif event["event_type"] == "EXPLORATION":
                    expl += 1

    stability_index = 1 - ((expl - inits) / (invoks - inits))

    return stability_index
