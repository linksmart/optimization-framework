import time


class ChargingStation:

    def __init__(self, charger, max_charging_power_kw, hosted_ev=None, soc=None, ev_unplugged=False):
        self.charger_id = charger
        self.max_charging_power_kw = max_charging_power_kw
        self.hosted_ev = None
        self.soc = soc  # TODO: 0 or None or soc?
        self.plugged = False
        self.recharge_start_time = None
        self.recharge_stop_time = None

        if hosted_ev:
            self.plug(hosted_ev, soc)

        if ev_unplugged:
            self.unplug()

    def plug(self, ev, soc):
        self.hosted_ev = ev
        if soc:
            self.soc = soc
        self.plugged = True
        if self.recharge_start_time is None:
            self.recharge_start_time = time.time()

    def unplug(self):
        # self.hosted_ev = None # TODO: should this be uncommented?
        self.plugged = False
        if self.recharge_stop_time is None:
            self.recharge_stop_time = time.time()

    def set_calculated_soc(self, soc):
        self.soc = soc

    def recharge_event(self, event, timestamp, hosted_ev = None):
        if isinstance(event, int):
            if event == 1:
                event = True
            else:
                event = False
        if isinstance(event, bool):
            if event:
                self.plug(hosted_ev, None)
                self.recharge_start_time = timestamp
            else:
                self.unplug()
                self.recharge_stop_time = timestamp

    def dict(self):
        return {"charger": self.charger_id,
         "max_charging_power_kw": self.max_charging_power_kw,
         "hosted_ev": self.hosted_ev,
         "soc": self.soc,
         "plugged": self.plugged,
         "recharge_start_time": self.recharge_start_time,
         "recharge_stop_time": self.recharge_stop_time
         }

    def __str__(self):
        return str(self.dict())