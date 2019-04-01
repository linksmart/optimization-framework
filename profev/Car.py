class Car:

    def __init__(self, car_name, battery_capacity):
        self.car_name = car_name
        self.battery_capacity = battery_capacity * 3600

    def charge(self, soc, charge_period, charge_power):
        return soc + charge_power * charge_period / self.battery_capacity
