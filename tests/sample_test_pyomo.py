import json
from pyomo.core import *
import pyomo.environ
from pyomo.opt import SolverFactory

data_dict = {
    "N" : {None:[0,1]},
    "T_SoC" : {None:[0]},
    "SoC_Value" : {0: {0:0.56, 1:12, 3:54}, 1 : {0: 0.23}}
}

for k, v in data_dict.items():
    if isinstance(v, dict):
        new_v = {}
        for k1, v1 in v.items():
            if k1 is not None and isinstance(k1, int) and isinstance(v1, dict):
                for k1, v1 in v.items():
                    for k2, v2 in v1.items():
                        new_v[k1, k2] = v2
        if len(new_v) > 0:
            data_dict[k] = new_v
data_dict = {None: data_dict}
print(data_dict)

#print("Data is: " + json.dumps(data_dict, indent=4))

model = AbstractModel()
model.N = Set()
model.T_SoC = Set()
model.SoC_Value = Param(model.N,model.T_SoC, within=PositiveReals)
model.SoC_Copy = Var(model.N, model.T_SoC, within=NonNegativeReals)

def con_rule_soc(model, n, t):
    return model.SoC_Copy[n,t] == model.SoC_Value[n,t]

model.con_soc_copy = Constraint(model.N, model.T_SoC, rule=con_rule_soc)

def obj_rule(model):
    return 1

model.obj = Objective(rule=obj_rule, sense=minimize)


solver_name = "ipopt"
model_path = "Maximize Self-Production_multiple.py"
instance = model.create_instance(data_dict)
optsolver = SolverFactory(solver_name)
result = optsolver.solve(instance, keepfiles=True)