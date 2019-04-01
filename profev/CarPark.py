class CarPark:

    def __init__(self, chargers_list, cars_list):

        self.cars = {}
        self.chargers = {}
        self.vac_capacity = 0
        self.total_charging_stations_power = 0

        for charger_index, charger in enumerate(chargers_list):
            self.chargers[charger_index] = charger
            self.total_charging_stations_power += charger.max_charging_power_kw

        for car_index, car in enumerate(cars_list):
            self.cars[car.car_name] = car
            self.vac_capacity += car.battery_capacity

        self.number_of_cars = len(self.cars)

    def max_charge_power_calculator(self, charging_period):
        """
        Returns a dictionary "connections"
            keys: charger labels
            values: max charging power input to the connected car
        """

        connections = {}
        for key, charger in self.chargers.items():
            hosted_car = charger.hosted_car
            if hosted_car:
                car = self.cars[hosted_car]
                battery_depth_of_discharge = (1 - charger.soc) * car.battery_capacity  # max_charging_power_kw-sec

                charger_limit = charger.max_charging_power_kw
                car_limit = battery_depth_of_discharge / charging_period

                connections[key] = min(charger_limit, car_limit)

        return connections
