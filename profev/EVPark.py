import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class CarPark:

    def __init__(self):

        self.cars = {}
        self.chargers = {}
        self.vac_capacity = 0
        self.total_charging_stations_power = 0

        for car_index, car in enumerate(cars_list):
            self.cars[car.car_name] = car
            self.vac_capacity += car.battery_capacity

        self.number_of_cars = len(self.cars)

    def add_evs(self, evs_list):
        for car_index, car in enumerate(evs_list):
            self.cars[car.car_name] = car
            self.vac_capacity += car.battery_capacity

    def add_chargers(self, chargers_list):
        for charger in chargers_list:
            if charger.charger_id in self.chargers.keys():
                self.update_charger(charger, charger.charger_id)
            else:
                self.chargers[charger.charger_id] = charger
                self.total_charging_stations_power += charger.max_charging_power_kw

    def update_charger(self, charger, charger_id):
        if charger_id in self.chargers.keys():
            old_charger = self.chargers[charger_id]
            if charger.has_ev():
                old_charger.plug(charger.hosted_car)
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
        logger.info("cars : "+str(self.cars))
        logger.info("chargers : "+str(self.chargers))
        for key, charger in self.chargers.items():
            hosted_car = charger.hosted_car
            logger.info("car "+str(hosted_car))
            if hosted_car:
                car = self.cars[hosted_car]
                battery_depth_of_discharge = (1 - charger.soc) * car.battery_capacity  # max_charging_power_kw-sec

                charger_limit = charger.max_charging_power_kw
                car_limit = battery_depth_of_discharge / charging_period

                connections[key] = min(charger_limit, car_limit)

        return connections
