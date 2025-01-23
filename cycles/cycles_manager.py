
from cycles.AH_cycle import cycle as AH_cycle
from cycles.CT_cycle import cycle as CTcycle
from DB.db_engine import engine
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo
import time
import threading

class cycles_manager:
    def __init__(self,mt5,remote_api,account):
        self.mt5 = mt5
        self.ah_repo = AHRepo(engine=engine)
        self.ct_repo = CTRepo(engine=engine)
        self.remote_api = remote_api
        self.all_AH_cycles = []
        self.remote_AH_cycles = []
        self.all_CT_cycles = []
        self.remote_CT_cycles = []
        self.account = account
    
     
    def get_all_AH_active_cycles(self):
        cycles = self.ah_repo.get_active_cycles()
        active_cycles = [cycle for cycle in cycles if cycle.is_closed is False]
        return active_cycles
    def get_all_CT_active_cycles(self):
        cycles = self.ct_repo.get_active_cycles()
        active_cycles = [cycle for cycle in cycles if cycle.is_closed is False]
        return active_cycles
    def  get_remote_AH_active_cycles(self):
        cycles = self.remote_api.get_all_AH_active_cycles_by_account(self.account.id)
        if cycles  is None:
            return []
        if len(cycles) == 0:
            return []
        
        active_cycles = [cycle for cycle in cycles if cycle.is_closed is False]
        return active_cycles
    def get_remote_CT_active_cycles(self):
        cycles = self.remote_api.get_all_CT_active_cycles_by_account(self.account.id)
        if cycles  is None:
            return []
        if len(cycles) == 0:
            return []
        active_cycles = [cycle for cycle in cycles if cycle.is_closed is False]
        return active_cycles
    # run in thread
    def run_cycles_manager(self):
        while True:
            self.sync_AH_cycles()
            self.sync_CT_cycles()
            time.sleep(2)
    def sync_AH_cycles(self):
        self.all_AH_cycles = self.get_all_AH_active_cycles()  # get all orders from MT5
        self.remote_AH_cycles= self.get_remote_AH_active_cycles() # get all orders from remote
        # check if the cycle is in the remote cycles and not in the local cycles
        for remote_cycle in self.remote_AH_cycles:
            cycle_id= remote_cycle.id
            if cycle_id not in [cycle.remote_id for cycle in self.all_AH_cycles]:
                cycle_data = self.ah_repo.get_cycle_by_remote_id(cycle_id)
                if cycle_data is not None:
                    cycle_obj = AH_cycle(cycle_data, self.mt5, self,"db")
                    self.remote_api.update_AH_cycle_by_id(cycle_obj.cycle_id,cycle_obj.to_remote_dict())
                if cycle_data is None:
                    cycle_obj = AH_cycle(remote_cycle, self.mt5, self,"remote")
                    self.ah_repo.create_cycle(cycle_obj.to_dict())
                        
        for cycle_data in self.all_AH_cycles:
            cycle_obj = AH_cycle(cycle_data, self.mt5, self,"db")
            self.remote_api.update_AH_cycle_by_id(cycle_obj.cycle_id,cycle_obj.to_remote_dict())
    def sync_CT_cycles(self):
        self.all_CT_cycles = self.get_all_CT_active_cycles()
        self.remote_CT_cycles= self.get_remote_CT_active_cycles()
        # check if the cycle is in the remote cycles and not in the local cycles
        for remote_cycle in self.remote_CT_cycles:
            cycle_id= remote_cycle.id
            if cycle_id not in [cycle.remote_id for cycle in self.all_CT_cycles] :
                cycle_data = self.ct_repo.get_cycle_by_remote_id(cycle_id)
                if cycle_data is not None:
                    cycle_obj = CTcycle(cycle_data, self.mt5, self,"db")
                    self.remote_api.update_CT_cycle_by_id(cycle_obj.cycle_id,cycle_obj.to_remote_dict())
                if cycle_data is None:
                    cycle_obj = CTcycle(remote_cycle, self.mt5, self,"remote")
                    self.ct_repo.create_cycle(cycle_obj.to_dict())
                    
        for cycle_data in self.all_CT_cycles:
            cycle_obj = CTcycle(cycle_data, self.mt5, self,"db")
            self.remote_api.update_CT_cycle_by_id(cycle_obj.cycle_id,cycle_obj.to_remote_dict())
            
                
    # run in thread
    def run_in_thread(self):
        cycles_manager_thread = threading.Thread(target=self.run_cycles_manager, daemon=True)
        # Start the thread
        cycles_manager_thread.start()            
