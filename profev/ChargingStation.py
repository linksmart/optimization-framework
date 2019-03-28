class ChargingStation:

    def __init__(self, max_charging_power_kw, hosted_car=None, soc=None):
        self.max_charging_power_kw = max_charging_power_kw
        self.hosted_car = hosted_car
        self.soc = soc
        self.plugged = False

        if hosted_car:
            self.hosted_car = hosted_car
            self.plugged = True
            self.soc = soc

    def plug(self, car):
        self.hosted_car = car
        self.plugged = True

    def unplug(self):
        self.hosted_car = None
        self.plugged = False

    def charge(self, charge_period, charge_power):

        if self.plugged == 1:
            self.soc = self.hosted_car.charge(self.soc, charge_period, charge_power)
        else:
            print("Charge decision cannot be implemented")
