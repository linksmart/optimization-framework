class EV:

    def __init__(self, ev_name, battery_capacity):
        self.ev_name = ev_name
        self.battery_capacity = battery_capacity

    def charge(self, soc, charge_period, charge_power):
        return soc + charge_power * charge_period / self.battery_capacity

    def __repr__(self):
        return self.ev_name

    def __str__(self):
        return self.ev_name