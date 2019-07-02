import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class EVPark:

    def __init__(self):

        self.evs = {}
        self.chargers = {}
        self.total_charging_stations_power = 0

    def add_evs(self, evs_list):
        for ev in evs_list:
            self.evs[ev.ev_name] = ev

    def get_num_of_cars(self):
        return len(self.evs)

    # TODO: should it be calculated only for hosted evs?
    def get_vac_capacity(self):
        vac_capacity = 0
        for ev_name, ev in self.evs.items():
            vac_capacity += ev.battery_capacity
        return vac_capacity

    def add_chargers(self, chargers_list):
        for charger in chargers_list:
            self.validate_hosted_ev(charger)
            if charger.charger_id in self.chargers.keys():
                self.update_charger(charger, charger.charger_id)
            else:
                self.chargers[charger.charger_id] = charger
                self.total_charging_stations_power += charger.max_charging_power_kw

    def validate_hosted_ev(self, charger):
        if charger.hosted_ev is not None and charger.hosted_ev not in self.evs.keys():
            raise Exception("EV "+str(charger.hosted_ev)+" hosted on charger "+str(charger.charger_id)+" but not registered")

    def update_charger(self, charger, charger_id):
        if charger_id in self.chargers.keys():
            old_charger = self.chargers[charger_id]
            if charger.has_ev():
                old_charger.plug(charger.hosted_ev)
            elif old_charger.has_ev():
                old_charger.unplug()

    def remove_ev(self, ev):
        pass

    def max_charge_power_calculator(self, charging_period):
        """
        Returns a dictionary "connections"
            keys: charger labels
            values: max charging power input to the connected car
        """

        connections = {}
        logger.info("evs : " + str(self.evs))
        logger.info("chargers : "+str(self.chargers))
        for key, charger in self.chargers.items():
            hosted_ev = charger.hosted_ev
            logger.info("ev "+str(hosted_ev))
            if hosted_ev:
                ev = self.evs[hosted_ev]
                battery_depth_of_discharge = (1 - charger.soc) * ev.battery_capacity * 3600 # max_charging_power_kw-sec

                charger_limit = charger.max_charging_power_kw
                car_limit = battery_depth_of_discharge / charging_period

                connections[key] = min(charger_limit, car_limit)

        return connections

    def get_hosted_ev(self, charger_id):
        if charger_id and charger_id in self.chargers.keys():
            return self.chargers[charger_id].hosted_ev

    # TODO: include all evs for calculation
    def calculate_vac_soc_value(self):
        vac_soc_value = 0
        vac = 0
        logger.info(self.chargers.keys())
        logger.info(self.evs.keys())
        for key, charger in self.chargers.items():
            logger.info("charger "+str(key)+" "+str(charger.hosted_ev))
            if charger.hosted_ev in self.evs.keys():
                ev = self.evs[charger.hosted_ev]
                logger.info("inside "+str(ev.battery_capacity))
                vac_soc_value += charger.soc * ev.battery_capacity
                vac += ev.battery_capacity
        logger.info("cal "+str(vac_soc_value)+ " "+ str(vac))
        if vac <= 0:
            vac_soc_value = 0
        else:
            vac_soc_value = vac_soc_value * 100 / vac
        return vac_soc_value
