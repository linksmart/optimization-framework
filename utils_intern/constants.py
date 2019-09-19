"""
Created on Aug 09 10:36 2018

@author: nishit
"""


class Constants:
    ESS = "ESS"
    SoC_Value = "SoC_Value"
    meta = "meta"
    P_PV = "P_PV"
    P_Load = "P_Load"
    Q_Load = "Q_Load"
    mqtt = "mqtt"
    unit = "unit"
    CarPark = "EVPark"
    Uncertainty = "Uncertainty"

    name_server_key = "name_server"
    dispatch_server_key = "dispatch_server"
    pyro_mip = "pyro_mip"
    pyro_mip_pid = "pyro_mip_pid"
    name_server_command = "/usr/local/bin/pyomo_ns -n localhost"
    dispatch_server_command = "/usr/local/bin/dispatch_srvr -n localhost"
    pyro_mip_server_command = "/usr/local/bin/pyro_mip_server"
    id_meta = "id_meta"

    repetition = "repetition"
    optimization_type = "optimization_type"
    lock_key = "id_lock"