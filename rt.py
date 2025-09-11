#from simulation import Simulation
import os
import time
from datetime import datetime
from multiprocessing.managers import BaseManager

#tmpfldr = os.path.abspath(os.path.join(os.path.dirname(__file__), consts.TEMP_FILES_DIR))
#REALTIME_FILE=tmpfldr+"/REALTIME"

REALTIME_FILE=os.path.abspath(os.path.join(os.path.dirname(__file__), "mab-automated-experiments/-temp/REALTIME"))
REALTIME_INTERVAL=2 # [s]
REALTIME_ETC_THRESHOLD=500 # [s]
#rt_dict= {}

# for the monitoring thread
def monitor_storage(shared_custom, stop_event):
    print("[rt]starting monitoring...")
    while not stop_event.is_set():
        storage_content = shared_custom.print_table()
        #print(f"Stato attuale del tracker: {storage_content}")
        # Controlla lo stato ogni 0.5 secondi
        time.sleep(REALTIME_INTERVAL)

class RealTimeTracker:
    def __init__(self):
        print("[rt] initializing")
        #todo la creazione della directory, fatta a parte, magari anche parametrizzando il percorso
        path = os.path.join(os.path.dirname(__file__), "mab-automated-experiments/-temp")
        if not os.path.exists(path): os.makedirs(path)
        #print(REALTIME_FILE)
        #with open("bayesopt-realtime-track.yml", "w+") as rtfile:
            #rtfile.write(str([v for _, v in rt_dict.items()]))
        #    rtfile.write("oooooooooo\n")
            #rtfile.write(str([s for s in self.simulations]))
        #    rtfile.write("E")
        self.simulations= {}
        #exit(1)

    #def append_sim(self, sim, pid:int):
    def append_sim(self):
        #self.simulations.append(PerSimulationRealTimeTrack(sim, pid))
        self.simulations.append("W")
        #with open("bayesopt-realtime-track.yml", "w+") as rtfile:
            #rtfile.write(str([v for _, v in rt_dict.items()]))
        #    rtfile.write("*** REAL-TIME SIMULATIONS STATS ***\n")
            #rtfile.write(str([s for s in self.simulations]))
            #rtfile.write("Ew")

    def _are_all_stats_ready(self) -> bool:
        return not any(val == "N/A" for sottodiz in self.simulations.values() for val in sottodiz.values())

    def print_table(self):
        table=""
        #table="no.\t"
        table+="pid\t"

        unique_keys=["time", "end", "pct", "ETC"]
        excluded_keys=["last_time_measure"]

        for pid, data in self.simulations.items():
            for subkey in data.keys():
                if subkey not in unique_keys and subkey not in excluded_keys:
                    unique_keys.append(subkey)
        for k in unique_keys:
            table+=str(k)+"\t"
            #time\tbayes_iter\n"
        table+="\n"
        i=0
        for pid,data in self.simulations.items():
            i+=1
            pct=data.get("time",-1)/data.get("end",+1)
            if pct==-1.0: pct="N/A"
            else: pct=str(round(pct*100,1))+"%"
            data["pct"]=pct
            #table+=str(i)+"\t"
            table+=str(pid)
            #print(data,unique_keys)

            # check for probable stuck simulations
            now=datetime.now()
            delta=now-data.get("last_time_measure", now)
            if delta.total_seconds()>20: # TODO parametrizzare
                    table+=f"\t[*** NO DATA SINCE {delta.seconds} s *** possibly dead?]"
            else:
                for subkey in unique_keys:
                        table+="\t"+str(data.get(subkey, "N/A"))[:7]
            table+="\n"
        table+="\n-------------------------------\n"
        table+=f"{len(self.simulations)} simulations running."

        with open(REALTIME_FILE, "w+") as rtfile:
            #rtfile.write(str([data for _, data in rt_dict.items()]))
            rtfile.write("*** REAL-TIME SIMULATIONS STATS ***\n")
            if not self._are_all_stats_ready():
                rtfile.write("(some stats are still loading, please wait...)\n")
            else:
                rtfile.write("\n")
            rtfile.write(table)

    def update(self, pid, key, val):
        if pid not in self.simulations:
            self.simulations[pid] = {}
        if key=="time":
            old=self.simulations[pid].get("time", 0)
            now=datetime.now()
            delta=now-self.simulations[pid].get("last_time_measure", now)
            end=self.simulations[pid].get("end", "N/A")
            self.simulations[pid]["ETC"]=str((delta*(end-val))/(val-old))[:7]
            self.simulations[pid]["last_time_measure"]=now
        self.simulations[pid][key]=val

    def end(self, pid):
        if pid not in self.simulations: raise ValueError()
        self.simulations.pop(pid)


# custom manager to support custom classes
class CustomManager(BaseManager):
    # nothing
    pass

#bigrtt=RealTimeTracker()


