from enum import Enum, auto


class MABEventFlag(Enum):
    INITIALIZATION=auto()
    EXPLORATION=auto()
    #EXPLOITATION=auto()
    CONTEXT_INSTANCE_CHANGE_OLD=auto()
    CONTEXT_INSTANCE_CHANGE_NEW=auto()
    MAB_KNOWLEDGE_INHERITANCE_PREDECESSOR=auto()
    MAB_KNOWLEDGE_INHERITANCE_SUCCESSOR=auto()
    MAB_KNOWLEDGE_REFINING=auto()
    DISCARDED_REWARD=auto()
    EPOCH_RESET=auto()
    EPOCH_START=auto()

    def __repr__(self):
        return str(self.name)

class MABEvent():
    def __init__(self, agent_label:str, event_type:MABEventFlag, time:float):
        self.agent_label=agent_label
        self.event_type=event_type
        self.time=time

    def register_event(self, event:MABEventFlag):
        self.events_occurred.append([event])
