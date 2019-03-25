class CarPark:

    def __init__(self, charger_list, car_list):

        self.cars = {}
        self.chargers = {charger_index: charger for charger_index, charger in enumerate(charger_list)}
        self.vac_capacity = 0

        for car_index, car in enumerate(car_list):
            self.cars[car_index] = car
            self.vac_capacity += car.batteryCapacity

        self.number_of_cars = len(self.cars)

    def max_charge_power_calculator(self, charging_period):
        """
        Returns a dictionary "connections"
            keys: charger labels
            values: max charging power input to the connected car
        """

        connections = {}
        for key, charger in self.chargers.items():
            if charger.hosted_car:
                car = charger.hosted_car
                battery_depth_of_discharge = (1 - charger.soc) * car.batteryCapacity  # max_charging_power_kw-sec

                charger_limit = charger.kW
                car_limit = battery_depth_of_discharge / charging_period

                connections[key] = min(charger_limit, car_limit)

        return connections
