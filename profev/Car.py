class Car:

    def __init__(self, battery_capacity):
        self.batteryCapacity = battery_capacity * 3600

    def charge(self, soc, charge_period, charge_power):
        return soc + charge_power * charge_period / self.batteryCapacity
