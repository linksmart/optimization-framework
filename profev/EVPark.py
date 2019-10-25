from utils_intern.messageLogger import MessageLogger

class EVPark:

    def __init__(self, id):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.evs = {}
        self.chargers = {}
        self.total_charging_stations_power = 0

    def add_evs(self, evs_list):
        for ev in evs_list:
            if ev.ev_name in self.evs.keys():
                self.evs[ev.ev_name].update(ev.battery_capacity)
            else:
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
            if charger.hosted_ev:
                old_charger.plug(charger.hosted_ev, charger.soc)
            elif old_charger.hosted_ev:
                old_charger.unplug()
            if charger.max_charging_power_kw:
                old_charger.max_charging_power_kw = charger.max_charging_power_kw

    def remove_ev(self, ev):
        pass

    def max_charge_power_calculator(self, charging_period):
        """
        Returns a dictionary "connections"
            keys: charger labels
            values: max charging power input to the connected car
        """

        connections = {}
        self.logger.info("evs : " + str(self.evs))
        self.logger.info("chargers : "+str(self.chargers))
        for key, charger in self.chargers.items():
            hosted_ev = charger.hosted_ev
            self.logger.info("ev "+str(hosted_ev))
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

    def avg_battery_capacity(self):
        avg = 0
        for ev_id, ev in self.evs.items():
            avg += ev.battery_capacity
        avg = avg/len(self.evs)
        return avg

    # TODO: include all evs for calculation
    def calculate_vac_soc_value(self, vac_soc_value_override=None):
        default = 50
        vac_soc_value = 0
        vac = 0
        all_soc_present = True
        avg_battery_cap = self.avg_battery_capacity()
        self.logger.info(self.chargers.keys())
        self.logger.info(self.evs.keys())
        for key, charger in self.chargers.items():
            self.logger.info("charger "+str(key)+" "+str(charger.hosted_ev))
            if charger.hosted_ev in self.evs.keys():
                ev = self.evs[charger.hosted_ev]
                self.logger.info("inside "+str(ev.battery_capacity))
                vac_soc_value += charger.soc * ev.battery_capacity
                vac += ev.battery_capacity
            elif charger.soc is not None:
                vac_soc_value += charger.soc * avg_battery_cap
                vac += avg_battery_cap
            else:
                all_soc_present = False
        self.logger.info("cal "+str(vac_soc_value)+ " "+ str(vac))
        if vac <= 0:
            vac_soc_value = 0
        else:
            vac_soc_value = vac_soc_value * 100 / vac
        if not all_soc_present:
            vac_soc_value = default
            self.logger.info("Not all soc values present so using default vac_soc_value of "+str(default))
        if vac_soc_value_override is not None:
            vac_soc_value = vac_soc_value_override
            self.logger.info("vac_soc_value_override to "+str(vac_soc_value_override))
        return vac_soc_value

    def charge_ev(self, p_ev, dT):
        self.logger.debug("p_ev: "+str(p_ev))
        socs = {}
        for key, charger in self.chargers.items():
            if key in p_ev.keys():
                self.logger.info("charging " + str(charger.__str__()))
                hosted_ev = charger.hosted_ev
                soc = charger.soc
                if hosted_ev in self.evs.keys() and charger.plugged:
                    new_soc = self.evs[hosted_ev].charge(soc, dT, p_ev[key])
                    self.logger.debug("new soc = "+str(new_soc))
                    charger.set_calculated_soc(new_soc)
                    self.logger.info("charged " + str(charger.__str__()))
                    socs[key] = new_soc
                elif hosted_ev in self.evs.keys():
                    new_soc = self.evs[hosted_ev].discharge(soc)
                    charger.set_calculated_soc(new_soc)
                    self.logger.info("discharged " + str(charger.__str__()))
                    socs[key] = new_soc
                else:
                    self.logger.error("Charger "+charger.charger_id+" does not have hosted ev so cannot calculate soc")
            else:
                self.logger.info("discharging " + str(charger.__str__()))
                soc = charger.soc
                hosted_ev = charger.hosted_ev
                if hosted_ev in self.evs.keys():
                    new_soc = self.evs[hosted_ev].discharge(soc)
                    charger.set_calculated_soc(new_soc)
                    self.logger.info("discharged " + str(charger.__str__()))
                    socs[key] = new_soc
                else:
                    self.logger.error("Charger "+charger.charger_id+" does not have hosted ev so cannot calculate soc")
        return socs

    def single_ev_recharge(self):
        if len(self.chargers) == 1:
            for charger_id, charger in self.chargers.items():
                if charger.plugged:
                    return 1
        return 0