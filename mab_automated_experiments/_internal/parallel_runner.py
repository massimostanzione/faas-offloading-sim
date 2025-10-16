import math
import multiprocessing
import threading

from rt import CustomManager, RealTimeTracker, monitor_storage


def run_parallel_executions(max_parallel_executions, instances_list, fn):
    effective_procs = max(1, min(len(instances_list), max_parallel_executions))
    cs = max(1, math.ceil(len(instances_list) / effective_procs))
    print("[parall]need to run ", len(instances_list), "executions, on ", effective_procs, "processors, grouped by ",
          cs)

    CustomManager.register('RealTimeTracker', RealTimeTracker)
    with CustomManager() as manager:
        tracker = manager.RealTimeTracker()

        # start monitoring thread
        stop_event = threading.Event()
        monitor_thread = threading.Thread(target=monitor_storage, args=(tracker, stop_event))
        monitor_thread.start()

        args_list = [(tracker, i) for i in instances_list]

        with multiprocessing.Pool(processes=effective_procs) as pool:
            # start processes in an async way
            results = pool.starmap_async(fn, args_list, chunksize=cs)

            print("\n[parall]pool started, waiting for them to finish...")

            # wait
            results.get()

        # processes terminated, stop monitoring thread
        stop_event.set()
        monitor_thread.join()

        print("\n[parall]done")
