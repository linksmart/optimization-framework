class ChargingStation:

    def __init__(self, charger, max_charging_power_kw, hosted_ev=None, soc=None):
        self.charger_id = charger
        self.max_charging_power_kw = max_charging_power_kw
        self.hosted_ev = hosted_ev
        self.soc = soc
        self.plugged = False

        if hosted_ev:
            self.hosted_ev = hosted_ev
            self.plugged = True
            self.soc = soc

    def plug(self, ev):
        self.hosted_ev = ev
        self.plugged = True

    def unplug(self):
        self.hosted_ev = None
        self.plugged = False

    def charge(self, charge_period, charge_power):

        if self.plugged == 1:
            self.soc = self.hosted_ev.charge(self.soc, charge_period, charge_power)
        else:
            print("Charge decision cannot be implemented")
