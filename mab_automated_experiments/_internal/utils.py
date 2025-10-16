DEFAULT_POLICY_COLOR = "black"

policy_colors = {
    "random-lb": "green",
    "round-robin-lb": "blue",
    "mama-lb": "orange",
    "const-hash-lb": "purple",
    "wrr-speedup-lb": "lawngreen",
    "wrr-memory-lb": "dodgerblue",
    "wrr-cost-lb": "fuchsia"
}


def get_policy_colors():
    return policy_colors


def get_color_for_policy(policy_name: str) -> str:
    val = policy_colors.get(policy_name, DEFAULT_POLICY_COLOR)
    if val is None:
        print("[WARNING] color not found for policy:", policy_name)
    return val
