from enum import Enum
from typing import Optional
from typing_extensions import deprecated

import conf
from conf import MAB_REWARD_CHANGE_AXIS_TIME
from simulation import RewardConfig


class RewardFnAxis(str, Enum):
    LOADIMB = "load_imb"
    RESPONSETIME = "rt"
    COST = "cost"
    UTILITY = "utility"
    VIOLATIONS = "violations"
    COLD_STARTS = "cold_starts"

    @staticmethod
    def _human_readable_values():
        return {
            RewardFnAxis.LOADIMB.value: "Load imbalance",
            RewardFnAxis.RESPONSETIME.value: "Response time",
            RewardFnAxis.COST.value: "Cost",
            RewardFnAxis.UTILITY.value: "Utility",
            RewardFnAxis.VIOLATIONS.value: "Violations",
            RewardFnAxis.COLD_STARTS.value: "Cold starts",
        }

    def to_human_readable(self):
        return RewardFnAxis._human_readable_values()[self.value]

    @staticmethod
    def get_values() -> list:
        return [axis.value for axis in RewardFnAxis]

    @staticmethod
    def is_valid(value: str) -> bool:
        return value in RewardFnAxis.get_values()

    @staticmethod
    def to_human_readable_by_value(value: str):
        if value not in RewardFnAxis.get_values():
            raise ValueError(f"Cannot find {value} into available axes human readable values.")
        return RewardFnAxis._human_readable_values()[value]


@deprecated("Please use RewardFnAxis.to_human_readable_by_value() instead.")
def get_axis_name_hr(axis: str):
    return RewardFnAxis._human_readable_values()[axis]


class RewardFunctionRepresentation:
    def __init__(self, reward_config: RewardConfig, axis_pre: RewardFnAxis, axis_post: RewardFnAxis,
                 change_axis_time: float, _subcall=False):
        if not _subcall:
            raise RuntimeError("Please call this class via ._by_reward_config() or .by_axes() methods.")

        # sanity checks are already run into the caller functions, here this assertion is more than sufficient
        assert ((axis_pre is not None and axis_post is not None) ^ (reward_config is not None))

        self.reward_config = reward_config
        self.axis_pre = axis_pre
        self.axis_post = axis_post
        self.change_axis_time = change_axis_time  # Please expand if you want to try non-stationary environments

    def __str__(self):
        if self.is_by_reward_config(): return self.reward_config.__str__()
        if self.is_by_axes():
            if self.is_static_environment():
                return f"Reward fn.: 1*{self.axis_pre}"
            else:
                return f"<axis_{{pre,post}}={{{self.axis_pre},{self.axis_post}}};CAT={self.change_axis_time}>"
        return RuntimeError("iii")

    def __repr__(self):
        if self.is_by_reward_config(): return self.reward_config
        if self.is_by_axes(): return f"<axis_{{pre,post}}={{{self.axis_pre},{self.axis_post}}};CAT={self.change_axis_time}>"
        return RuntimeError("iii2")

    def __eq__(self, other):
        if not isinstance(other, RewardFunctionRepresentation):
            return NotImplemented
        if self.is_by_reward_config():
            return self.reward_config == other.reward_config
        elif self.is_by_axes():
            return self.axis_pre == other.axis_pre and self.axis_post == other.axis_post
        else:
            raise RuntimeError("isdufhais")

    @classmethod
    def by_reward_config(cls, reward_config: RewardConfig, change_axis_time: float = None):
        if reward_config is None: raise RuntimeError("ihuihui")
        return cls(reward_config, None, None, change_axis_time, True)

    @classmethod
    def by_axes(cls, axis_pre: RewardFnAxis, axis_post: RewardFnAxis = None, change_axis_time: float = None):
        if axis_pre is None: raise ValueError(f"Axis_pre is none")
        if axis_post is None: axis_post = axis_pre  # static
        return cls(None, axis_pre, axis_post, change_axis_time, True)

    @classmethod
    def by_axes_as_strings(cls, axis_pre: str, axis_post: str = None, change_axis_time=None):
        if axis_pre is None: raise ValueError(f"Axis_pre is none")
        if axis_post is None: axis_post = axis_pre  # static
        axes = [axis_pre, axis_post]

        # Sanity checks on strings
        for i, axis in enumerate(axes):
            if not RewardFnAxis.is_valid(axis): raise ValueError(
                f"Axis value \"{axis}\" is not valid.\nAvailable values:{RewardFnAxis.get_values()}")

        return RewardFunctionRepresentation.by_axes(
            RewardFnAxis(axis_pre),
            RewardFnAxis(axis_post),
            change_axis_time
        )

    def is_by_reward_config(self) -> bool:
        return self.reward_config is not None

    def is_by_axes(self) -> bool:
        return self.axis_pre is not None and self.axis_post is not None

    def is_static_environment(self) -> bool:
        if self.is_by_reward_config():
            return self.reward_config.is_static_environment()
        elif self.is_by_axes():
            return self.axis_pre == self.axis_post and self.axis_pre is not None

    def get_representation(self):
        if self.is_by_axes(): return self.axis_pre, self.axis_post
        if self.is_by_reward_config(): return self.reward_config
        raise RuntimeError("uiui")

    def convert_to_axis_representation(self, both_or_nothing: bool = True) -> (
            Optional[RewardFnAxis], Optional[RewardFnAxis]):

        if not self.is_by_reward_config(): return None

        # if this sanity check does not pass, it is useless to continue
        self.reward_config.check_sum()

        ret_pre = None
        ret_post = None

        for i, wght_pre in enumerate(self.reward_config.get_weights_pre()):
            if wght_pre == 1:
                ret_pre = list(RewardFnAxis)[i]
                break

        for i, wght_post in enumerate(self.reward_config.get_weights_post()):
            if wght_post == 1:
                ret_post = list(RewardFnAxis)[i]
                break

        if both_or_nothing:
            if ret_pre is None or ret_post is None:
                ret_pre = None
                ret_post = None
        return ret_pre, ret_post


class RewardFunctionIdentifierConverter:
    @staticmethod
    def to_identifiers_dictDEPRECATO(reward_function: RewardFunctionRepresentation) -> dict:
        if not reward_function.is_by_reward_config(): raise RuntimeError(
            "Cannot convert to rewconf dict, this representation is not rewconf.")
        return {
            "alpha": reward_function.reward_config.alpha,
            "beta": reward_function.reward_config.beta,
            "gamma": reward_function.reward_config.gamma,
            "delta": reward_function.reward_config.delta,
            "zeta": reward_function.reward_config.zeta,
            "eta": reward_function.reward_config.eta,

            "alpha_post": reward_function.reward_config.alpha_post,
            "beta_post": reward_function.reward_config.beta_post,
            "gamma_post": reward_function.reward_config.gamma_post,
            "delta_post": reward_function.reward_config.delta_post,
            "zeta_post": reward_function.reward_config.zeta_post,
            "eta_post": reward_function.reward_config.eta_post,

            "change_axis_time": reward_function.change_axis_time
        }

    @staticmethod
    def to_reward_config_dict(reward_function: RewardFunctionRepresentation) -> dict:
        if not reward_function.is_by_reward_config(): raise RuntimeError(
            "Cannot convert to rewconf dict, this representation is not rewconf.")
        return {
            conf.MAB_REWARD_ALPHA: reward_function.reward_config.alpha,
            conf.MAB_REWARD_BETA: reward_function.reward_config.beta,
            conf.MAB_REWARD_GAMMA: reward_function.reward_config.gamma,
            conf.MAB_REWARD_DELTA: reward_function.reward_config.delta,
            conf.MAB_REWARD_ZETA: reward_function.reward_config.zeta,
            conf.MAB_REWARD_ETA: reward_function.reward_config.eta,

            conf.MAB_REWARD_ALPHA_POST: reward_function.reward_config.alpha_post,
            conf.MAB_REWARD_BETA_POST: reward_function.reward_config.beta_post,
            conf.MAB_REWARD_GAMMA_POST: reward_function.reward_config.gamma_post,
            conf.MAB_REWARD_DELTA_POST: reward_function.reward_config.delta_post,
            conf.MAB_REWARD_ZETA_POST: reward_function.reward_config.zeta_post,
            conf.MAB_REWARD_ETA_POST: reward_function.reward_config.eta_post,

            conf.MAB_REWARD_CHANGE_AXIS_TIME: reward_function.change_axis_time
        }

    @staticmethod
    def _to_reward_config_repr(identifiers_dict: dict, rewconf_key="reward_config") -> RewardFunctionRepresentation:
        reward_config_dict = identifiers_dict[rewconf_key]
        rewconf = RewardConfig(
            float(reward_config_dict[conf.MAB_REWARD_ALPHA] if conf.MAB_REWARD_ALPHA in reward_config_dict else 0),
            float(reward_config_dict[conf.MAB_REWARD_BETA] if conf.MAB_REWARD_BETA in reward_config_dict else 0),
            float(reward_config_dict[conf.MAB_REWARD_GAMMA] if conf.MAB_REWARD_GAMMA in reward_config_dict else 0),
            float(reward_config_dict[conf.MAB_REWARD_DELTA] if conf.MAB_REWARD_DELTA in reward_config_dict else 0),
            float(reward_config_dict[conf.MAB_REWARD_ZETA] if conf.MAB_REWARD_ZETA in reward_config_dict else 0),
            float(reward_config_dict[conf.MAB_REWARD_ETA] if conf.MAB_REWARD_ETA in reward_config_dict else 0),

            float(reward_config_dict[
                      conf.MAB_REWARD_ALPHA_POST] if conf.MAB_REWARD_ALPHA_POST in reward_config_dict else (
                reward_config_dict[conf.MAB_REWARD_ALPHA] if conf.MAB_REWARD_ALPHA in reward_config_dict else 0)),
            float(
                reward_config_dict[conf.MAB_REWARD_BETA_POST] if conf.MAB_REWARD_BETA_POST in reward_config_dict else (
                    reward_config_dict[conf.MAB_REWARD_BETA] if conf.MAB_REWARD_BETA in reward_config_dict else 0)),
            float(reward_config_dict[
                      conf.MAB_REWARD_GAMMA_POST] if conf.MAB_REWARD_GAMMA_POST in reward_config_dict else (
                reward_config_dict[conf.MAB_REWARD_GAMMA] if conf.MAB_REWARD_GAMMA in reward_config_dict else 0)),
            float(reward_config_dict[
                      conf.MAB_REWARD_DELTA_POST] if conf.MAB_REWARD_DELTA_POST in reward_config_dict else (
                reward_config_dict[conf.MAB_REWARD_DELTA] if conf.MAB_REWARD_DELTA in reward_config_dict else 0)),
            float(
                reward_config_dict[conf.MAB_REWARD_ZETA_POST] if conf.MAB_REWARD_ZETA_POST in reward_config_dict else (
                    reward_config_dict[conf.MAB_REWARD_ZETA] if conf.MAB_REWARD_ZETA in reward_config_dict else 0)),
            float(reward_config_dict[conf.MAB_REWARD_ETA_POST] if conf.MAB_REWARD_ETA_POST in reward_config_dict else (
                reward_config_dict[conf.MAB_REWARD_ETA] if conf.MAB_REWARD_ETA in reward_config_dict else 0))
        )
        return RewardFunctionRepresentation.by_reward_config(
            rewconf,
            reward_config_dict[
                MAB_REWARD_CHANGE_AXIS_TIME] if MAB_REWARD_CHANGE_AXIS_TIME in reward_config_dict else None
        )

    @staticmethod
    def _to_axes_repr(reward_config_dict: dict) -> RewardFunctionRepresentation:
        return RewardFunctionRepresentation.by_axes(
            reward_config_dict["axis_pre"],
            reward_config_dict["axis_post"],
            reward_config_dict[
                MAB_REWARD_CHANGE_AXIS_TIME] if MAB_REWARD_CHANGE_AXIS_TIME in reward_config_dict else None
        )

    @staticmethod
    def is_identifier_exp_dict_by_reward_config(identifiers_exp_dict: dict) -> bool:
        return "reward_config" in identifiers_exp_dict

    @staticmethod
    def is_identifier_exp_dict_by_axes(identifiers_exp_dict: dict) -> bool:
        return "axis_pre" in identifiers_exp_dict

    @classmethod
    def append_reward_function(cls, reward_function: RewardFunctionRepresentation, identifiers_partial: dict) -> dict:
        # append to it the reward function representation
        if reward_function.is_by_axes():
            identifiers_partial["axis_pre"] = reward_function.axis_pre
            identifiers_partial["axis_post"] = reward_function.axis_post
        elif reward_function.is_by_reward_config():
            # try to convert to axis representation (it's simpler to debug)...
            conv_pre, conv_post = reward_function.convert_to_axis_representation(True)
            if conv_pre is not None and conv_post is not None:
                # ... if it is possible, log results identifying the by axes,
                identifiers_partial["axis_pre"] = conv_pre
                identifiers_partial["axis_post"] = conv_post
            else:
                # ... otherwise, just stick with the full reward config
                identifiers_partial["reward_config"] = RewardFunctionIdentifierConverter.to_reward_config_dict(
                    # )to_identifiers_dict(
                    reward_function)
        else:
            raise RuntimeError("Reward function representation type is undefined")
        return identifiers_partial

    @classmethod
    def deserialize_reward_function(cls, identifiers_dict) -> RewardFunctionRepresentation:
        if RewardFunctionIdentifierConverter.is_identifier_exp_dict_by_reward_config(identifiers_dict):
            return RewardFunctionIdentifierConverter._to_reward_config_repr(identifiers_dict)
        elif RewardFunctionIdentifierConverter.is_identifier_exp_dict_by_axes(identifiers_dict):
            return RewardFunctionIdentifierConverter._to_axes_repr(identifiers_dict)
        else:
            raise ValueError(
                f"Cannot grasp reward function type from deserialization, got identifiers_dict={identifiers_dict}")
