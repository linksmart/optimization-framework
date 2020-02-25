import datetime

from utils_intern.messageLogger import MessageLogger

class EV:

    def __init__(self, id, ev_name, battery_capacity, soc=1, consumption_pro_100_km = (11.7 / 100)):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.ev_name = ev_name
        self.battery_capacity = battery_capacity
        self.consumption = consumption_pro_100_km
        self.set_soc(soc)

    def set_soc(self, soc):
        if soc == None:
            self.logger.error("Soc could not be added")
        else:
            self.logger.debug("Setting soc of " + str(soc) + " for " + str(self.ev_name))
            self.calculated_soc = soc

    def get_soc(self):
        return self.calculated_soc

    def charge(self, soc, charge_period, charge_power, n_eff=1):
        if soc:
            self.calculated_soc = soc + (n_eff * charge_power * charge_period) / (self.battery_capacity * 3600) # multiplying to 3660 to convert to kws
            if self.calculated_soc > 1:
                self.calculated_soc = 1
        return self.calculated_soc

    def discharge(self, soc, discharge_period,  number_km_driven = 2):
        number_km_driven = self.number_of_km_driven(number_km_driven)
        if soc:
            self.calculated_soc = soc - ((self.consumption * number_km_driven * 3600) / (self.battery_capacity * 3600)) * (discharge_period / 3600) # consumption in 1 hr
            if self.calculated_soc < 0:
                self.calculated_soc = 0
        else:
            self.logger.debug("calculated_soc_before " + str(self.calculated_soc))
            self.calculated_soc = self.calculated_soc - ((self.consumption * number_km_driven * 3600) / (self.battery_capacity * 3600)) * (discharge_period / 3600) # consumption in 1 hr
            self.logger.debug("calculated_soc_after " + str(self.calculated_soc))
            if self.calculated_soc < 0:
                self.calculated_soc = 0
        return self.calculated_soc

    def number_of_km_driven(self, number_km_driven):
        current_hour = datetime.datetime.now().hour
        self.logger.debug("current_hour "+str(current_hour))
        if current_hour >= 21 and current_hour <= 6:
            return 0
        else:
            return number_km_driven

    def update(self, battery_capacity, consumption_pro_100_km = (11.7 / 100)):
        self.battery_capacity = battery_capacity
        self.consumption = consumption_pro_100_km

    def __repr__(self):
        return self.ev_name

    def __str__(self):
        return self.ev_name