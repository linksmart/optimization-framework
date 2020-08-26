from IO.ConfigParserUtils import ConfigParserUtils
from IO.inputConfigParser import InputConfigParser


m = {
  "generic": {
    "custom_1": [
      {
        "datalist": [
          12,
          10
        ],
        "meta": {
          "meta_1": 0.9
        }
      },
      {
        "datalist": [
          11,
          13
        ],
        "meta": {
          "meta_2": 0.9
        }
      }
    ],
    "custom_2": [
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "predict"
        },
        "meta": {
          "meta_3": 0.9
        }
      }
    ],
    "meta": {
      "meta_4": 12
    }
  },
  "load": {
    "P_Load": [
      {
        "datalist": [
          12,
          10
        ],
        "meta": {
          "pf_Load": 0.9
        }
      },
      {
        "datalist": [
          11,
          13
        ],
        "meta": {
          "pf_Load": 0.9
        }
      },
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "predict"
        },
        "meta": {
          "pf_Load": 0.9
        }
      }
    ],
    "Q_Load": [
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "predict"
        },
        "meta": {
          "qpf_Load": 0.9
        }
      },
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "predict"
        },
        "meta": {
          "qpf_Load": 0.9
        }
      },
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "predict"
        },
        "meta": {
          "qpf_Load": 0.9
        }
      }
    ],
    "Q_Load_T": [
      {
        "datalist": [
          12,
          10
        ],
        "meta": {
          "qf_Load": 0.9
        }
      }
    ]
  },
  "ESS": {
    "SoC_Value": [
      {
        "datalist": [
          41
        ],
        "meta": {
          "ESS_Max_Discharge_Power": 2500,
          "ESS_Max_SoC": 90,
          "ESS_Charging_Eff": 0.9,
          "ESS_Min_SoC": 20,
          "ESS_Max_Charge_Power": 2500,
          "ESS_Discharging_Eff": 0.84999,
          "ESS_Capacity": 3560
        }
      },
      {
        "datalist": [
          41
        ],
        "meta": {
          "ESS_Max_Discharge_Power": 2500,
          "ESS_Max_SoC": 90,
          "ESS_Charging_Eff": 0.9,
          "ESS_Min_SoC": 20,
          "ESS_Max_Charge_Power": 2500,
          "ESS_Discharging_Eff": 0.84999,
          "ESS_Capacity": 3560
        }
      },
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name"
        },
        "meta": {
          "ESS_Max_Discharge_Power": 2500,
          "ESS_Max_SoC": 90,
          "ESS_Charging_Eff": 0.9,
          "ESS_Min_SoC": 20,
          "ESS_Max_Charge_Power": 2500,
          "ESS_Discharging_Eff": 0.84999,
          "ESS_Capacity": 3560
        }
      }
    ]
  },
  "grid": {
    "grid_1": [
      {
        "meta": {
          "Q_Grid_Max_Export_Power": 750,
          "Min_Voltage_Drop": 5,
          "P_Grid_Max_Export_Power": 1550,
          "Max_Voltage_Drop": 10
        }
      }
    ]
  },
  "photovoltaic": {
    "P_PV": [
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "pv_predict"
        },
        "meta": {
          "PV_Inv_Max_Power": 1300,
          "City": "Bonn",
          "Country": "Germany"
        }
      },
      {
        "datalist": [
          11,
          13
        ],
        "meta": {
          "PV_Inv_Max_Power": 1300,
          "City": "Aachen",
          "Country": "Germany"
        }
      }
    ],
    "Q_PV": [
      {
        "datalist": [
          12,
          10
        ],
        "meta": {
          "Q_PV_Inv_Max_Power": 1300,
          "City": "Bonn",
          "Country": "Germany"
        }
      },
      {
        "datalist": [
          11,
          13
        ],
        "meta": {
          "Q_PV_Inv_Max_Power": 1300,
          "City": "Aachen",
          "Country": "Germany"
        }
      }
    ]
  },
  "global_control": {
    "ESS_Control": [
      {
        "datalist": [
          12,
          10
        ],
        "meta": {
          "GlobalTargetWeight": 1,
          "LocalTargetWeight": 3
        }
      },
      {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
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
      "Unit_Drop_Penalty": 1,
      "VAC_SoC_Value_override": 20
    },
    "ev1": {
      "Battery_Capacity_kWh": 18.7
    },
    "ev2": {
      "Battery_Capacity_kWh": 18.7
    },
    "ev3": {
      "Battery_Capacity_kWh": 12.7
    }
  },
  "chargers": {
    "charger1": {
      "Max_Charging_Power_kW": 7,
      "Hosted_EV": "ev1",
      "SoC": {
        "datalist": [
          0.2
        ]
      }
    },
    "charger2": {
      "Max_Charging_Power_kW": 7,
      "Hosted_EV": "ev2",
      "SoC": {
        "datalist": [
          0.2
        ]
      }
    },
    "charger3": {
      "Max_Charging_Power_kW": 7,
      "SoC": {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "detachable": True,
          "option": "preprocess"
        }
      },
      "recharge": {
        "mqtt": {
          "qos": 1,
          "host": "hostname",
          "topic": "topic_name",
          "option": "event"
        }
      }
    }
  },
  "uncertainty": {
    "meta": {
      "monte_carlo_repetition": 10000
    },
    "Plugged_Time": {
      "mean": 18.76,
      "std": 1.3
    },
    "Unplugged_Time": {
      "mean": 7.32,
      "std": 0.78
    },
    "ESS_States": {
      "Min": 0,
      "Max": 100,
      "Steps": 10
    },
    "VAC_States": {
      "Min": 0,
      "Max": 100,
      "Steps": 2.5
    }
  }
}

mm = {
  "ESS": {
    "SoC_Value": [
      {
        "mqtt": {
          "host": "10.8.0.59",
          "topic": "/Fronius/SMX/ChaState",
          "qos": 1
        },
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
        "mqtt": {
          "host": "10.8.0.59",
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
  "photovoltaic": {
    "P_PV": [
      {
        "mqtt": {
          "host": "10.8.0.59",
          "topic": "/Fronius/SMX/PV_DCW",
          "qos": 1,
          "option": "pv_predict"
        },
        "meta": {
          "PV_Inv_Max_Power": 3.12,
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
    "T_SoC": 287,
    "Fronius_Max_Power": 5,
    "P_Grid_Input": [
      {
        "mqtt": {
          "host": "10.8.0.59",
          "topic": "/Fronius/SMX/W_Grid",
          "qos": 1
        }
      }
    ],
    "P_Load_Input": [
      {
        "mqtt": {
          "host": "10.8.0.59",
          "topic": "/Fronius/SMX/W_Load",
          "qos": 1
        }
      }
    ]
  }
}

mmm = {
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
          "option": "pv_predict_lstm"
        },
        "meta": {
          "PV_Inv_Max_Power": 10,
          "City": "Bolzano",
          "Country": "Italy"
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
      }
    ]
  }
}

#icp = InputConfigParser(input_config=mm, model_name="CarParkTest", id="asdf",
#                        optimization_type="stochastic", dT_in_seconds=3600, horizon_in_steps=24, persist_path="persist/asdf/persisted", restart=True)

#icp = InputConfigParser(input_config=mm, model_name="ResidentialMinGrid2", id="asdf",
#                        optimization_type="discrete", dT_in_seconds=3600, horizon_in_steps=24, persist_path="persist/asdf/persisted", restart=True)

icp = InputConfigParser(input_config=mmm, model_name="CarParkModelMinGridBolzano", id="asdf",
                        optimization_type="stochastic", dT_in_seconds=1800, horizon_in_steps=48,
                        persist_path="persist/asdf/persisted", restart=False)


# print(icp.model_variables)
print("______________")
print(icp.get_optimization_values())
print("_____________________")
for k, v in icp.name_params.items():
    print(k, v)
print("_____________________")
print(icp.check_keys_for_completeness())
print(icp.meta_values)
print(icp.set_params)