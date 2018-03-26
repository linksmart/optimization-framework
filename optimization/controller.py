# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

from pyomo.environ import SolverFactory
from optimization.ReferenceModel import model
import os

def start():
    project_dir=os.path.dirname(os.path.dirname(__file__))
    data_file=project_dir+"/optimization/data.dat"

    instance = model.create_instance(data_file)
    instance.pprint()

    opt=SolverFactory("glpk")
    results=opt.solve(instance)

    print(results)