import json
import time
from configparser import RawConfigParser

from senml import senml

from IO.inputConfigParser import InputConfigParser
from IO.inputPreprocess import InputPreprocess
from profev.ChargingStation import ChargingStation

m = {
  "load": {
    "P_Load": [
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "/Fronius/SMX/W_Load",
          "qos": 1,
          "option": "predict"
        },
        "meta": {
          "pf_Load": 1
        }
      }
    ]
  },
  "ESS": {
    "SoC_Value": [
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "/Fronius/SMX/ChaState",
          "qos": 1
        },
        "meta": {
          "ESS_Max_SoC": 1,
          "ESS_Max_Discharge_Power": 6.656,
          "ESS_Charging_Eff": 1,
          "ESS_Max_Charge_Power": 6.656,
          "ESS_Min_SoC": 0.2,
          "ESS_Discharging_Eff": 0.95,
          "ESS_Capacity": 9.6
        }
      }
    ]
  },
  "grid": {
    "grid_1": [
      {
        "meta": {
          "Max_Voltage_Drop": 1.1,
          "Min_Voltage_Drop": 0.9,
          "P_Grid_Max_Export_Power": 60,
          "Q_Grid_Max_Export_Power": 90
        }
      }
    ]
  },
  "photovoltaic": {
    "P_PV": [
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "/Fronius/SMX/PV_DCW",
          "qos": 1,
          "option": "pv_predict"
        },
        "meta": {
          "PV_Inv_Max_Power": 10,
          "City": "Bolzano",
          "Country": "Italy"
        }
      },
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "/Fronius/SMX/PV_DCW2",
          "qos": 1,
          "option": "pv_predict"
        },
        "meta": {
          "PV_Inv_Max_Power": 11,
          "City": "Fur",
          "Country": "Denmark"
        }
      }
    ]
  },
  "global_control": {
    "ESS_Control": [
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "SMX/Control/v1.0/Datastreams(166)/Observations",
          "qos": 1,
          "reuseable": True
        },
        "meta": {
          "GlobalTargetWeight": 1,
          "LocalTargetWeight": 3
        }
      }
    ]
  },
  "EV": {
    "meta": {
      "Unit_Consumption_Assumption": 2.5,
      "Unit_Drop_Penalty": 10,
      "VAC_SoC_Value_override": 20
    },
    "ev0": {
      "Battery_Capacity_kWh": 18.7
    },
    "ev1": {
      "Battery_Capacity_kWh": 18.7
    },
    "ev2": {
      "Battery_Capacity_kWh": 12.7
    }
  },
  "chargers": {
    "ASM_00000137-1-1": {
      "Max_Charging_Power_kW": 3.6,
      "SoC": {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "EV/Data",
          "qos": 1,
          "detachable": True,
          "option": "preprocess"
        }
      },
      "recharge": {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "EV/Data",
          "qos": 1,
          "option": "event"
        }
      }
    },
    "ASM_00000144-1-1": {
      "Max_Charging_Power_kW": 3.6,
      "SoC": {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "EV/Data",
          "qos": 1,
          "detachable": True,
          "option": "preprocess"
        }
      },
      "recharge": {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "EV/Data",
          "qos": 1,
          "option": "event"
        }
      }
    },
    "ASM_00000156-1-1": {
      "Max_Charging_Power_kW": 3.6,
      "SoC": {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "EV/Data",
          "qos": 1,
          "detachable": True,
          "option": "preprocess"
        }
      },
      "recharge": {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "EV/Data",
          "qos": 1,
          "option": "event"
        }
      }
    }
  },
  "uncertainty": {
    "ESS_States": {
      "Max": 100,
      "Min": 20,
      "Steps": 2.5
    },
    "Plugged_Time": {
      "mean": 11.13,
      "std": 2.4
    },
    "Unplugged_Time": {
      "mean": 6.86,
      "std": 2.42
    },
    "VAC_States": {
      "Max": 100,
      "Min": 0,
      "Steps": 2.5
    },
    "meta": {
      "monte_carlo_repetition": 1000
    }
  },
  "generic": {
    "P_PV_sample": [
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "con/opt/PV",
          "qos": 1,
          "option": "sampling"
        }
      }
    ],
    "P_Load_sample": [
      {
        "mqtt": {
          "host": "mosquito_S4G",
          "topic": "con/opt/Load",
          "qos": 1,
          "option": "sampling"
        }
      },
    ],
  }
}

mm = {
  "ESS": {
    "SoC_Value": [
      {
        "datalist": [0.56],
        "meta": {
          "ESS_Max_SoC": 1,
          "ESS_Max_Discharge_Power": 2.5,
          "ESS_Charging_Eff": 1,
          "ESS_Max_Charge_Power": 2.5,
          "ESS_Min_SoC": 0.2,
          "ESS_Discharging_Eff": 0.95,
          "ESS_Capacity": 3.6
        }
      },
      {
        "datalist": [0.23],
        "meta": {
          "ESS_Max_SoC": 1,
          "ESS_Max_Discharge_Power": 2.5,
          "ESS_Charging_Eff": 1,
          "ESS_Max_Charge_Power": 2.5,
          "ESS_Min_SoC": 0.2,
          "ESS_Discharging_Eff": 0.95,
          "ESS_Capacity": 3.6
        }
      }
    ]
  },
  "load": {
    "P_Load": [
      {
        "datalist": [
              0.57,
             0.906,
             0.906,
             0.70066667,
             0.77533333,
             0.906,
             0.906,
             1.0935,
             3.8135,
             14.73716667,
             9.88183333,
             24.413,
             4.216,
             2.1725,
             4.536,
             4.899,
             0.92466667,
             0.88733333,
             0.906,
             4.7475,
             4.8255,
             10.51866667,
             12.96316667,
             2.00733333
        ],
        "meta": {
          "pf_Load": 1
        }
      }
    ]
  },
  "photovoltaic": {
    "P_PV": [
      {
        "datalist": [
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          1.13248512,
          3.016735616,
          4.823979947,
          6.329861639,
          7.06663104,
          7.42742784,
          7.420178035,
          7.077290784,
          5.99361984,
          4.036273408,
          1.462618829,
          0,
          0,
          0,
          0,
          0
        ],
        "meta": {
          "PV_Inv_Max_Power": 20,
          "City": "Fur",
          "Country": "Denmark"
        }
      }
    ]
  },
  "grid": {
    "grid_1": [
      {
        "meta": {
          "Q_Grid_Max_Export_Power": 5,
          "P_Grid_Max_Export_Power": 5
        }
      }
    ]
  },
  "generic": {
  	"meta": {
  		"T_SoC": 1,
        "N": 2
  	}
  }
}


icp = InputConfigParser(input_config=mm, model_name="Maximize Self-Production_multiple", id="asdf",
                        optimization_type="dscrete", dT_in_seconds=3600, horizon_in_steps=24,
                        persist_path="persist/asdf/persisted", restart=False)
# print(icp.model_variables)
dd = icp.get_optimization_values()
print("______________")
print(dd)
print("______________")
for k, v in icp.name_params.items():
    print(k, v)
print("_____________________")
print(icp.check_keys_for_completeness())
print(icp.meta_values)
print(icp.set_params)
