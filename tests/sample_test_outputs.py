"""
Created on Dez 05 11:39 2019

@author: nishit
"""
from IO.ConfigParserUtils import ConfigParserUtils

o = {
  "generic": {
    "P_Fronius_Pct_Output": {
      "mqtt": {
        "qos": 1,
        "host": "10.8.0.59",
        "topic": "/PROFESS/SMX/InverterWControl"
      },
      "unit": "%",
      "horizon_values": False
    },
    "P_ESS_Output_Pct": {
      "mqtt": {
        "qos": 1,
        "host": "10.8.0.59",
        "topic": "/PROFESS/SMX/BatteryWControl"
      },
      "unit": "%",
      "horizon_values": False
    },
    "P_ESS_Output": {
      "mqtt": {
        "qos": 1,
        "host": "10.8.0.50",
        "topic": "/InstallationHouse20/PROFESS/P_ESS_Output",
        "port": 8883,
		"username": "fronius-fur",
		"password": "r>U@U7J8xZ+fu_vq",
		"ca_cert_path": "/usr/src/app/utils/s4g-ca.crt",
		"insecure": True
      },
      "unit": "kW",
      "horizon_values": False
    },
    "P_Fronius": {
      "mqtt": {
        "qos": 1,
        "host": "10.8.0.50",
        "topic": "/InstallationHouse20/PROFESS/P_Fronius",
        "port": 8883,
		"username": "fronius-fur",
		"password": "r>U@U7J8xZ+fu_vq",
		"ca_cert_path": "/usr/src/app/utils/s4g-ca.crt",
		"insecure": True
      },
      "unit": "kW",
      "horizon_values": False
    }
  },
    "error_calculation": {
      "P_Load": {
      "mqtt": {
        "qos": 1,
        "host": "10.8.0.50",
        "topic": "/InstallationHouse20/PROFESS/P_Fronius",
        "port": 8883,
		"username": "fronius-fur",
		"password": "r>U@U7J8xZ+fu_vq",
		"ca_cert_path": "/usr/src/app/utils/s4g-ca.crt",
		"insecure": True
      },
      "unit": "kW",
      "horizon_values": False
    }
    }
}


params = ConfigParserUtils.extract_mqtt_params_output(o, "error_calculation", True)

for k,v in params.items():
    print(k, v)