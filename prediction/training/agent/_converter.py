
from collections import OrderedDict
# import copy

# Features = OrderedDict([
#     ("Id",None),
#     ("Type",None),
#     ("ScreenPrinter/PositionX",0.),
#     ("ScreenPrinter/PositionY",0.),
#     ("PasteInspection/PosX1",0.),
#     ("PasteInspection/PosY1",0.),
#     ("PasteInspection/PosX2",0.),
#     ("PasteInspection/PosY2",0.),
#     ("PasteInspection/PosX3",0.),
#     ("PasteInspection/PosY3",0.),
#     ("PasteInspection/PosX4",0.),
#     ("PasteInspection/PosY4",0.),
#     ("PasteInspection/PosX5",0.),
#     ("PasteInspection/PosY5",0.),
#     ("PasteInspection/PosX6",0.),
#     ("PasteInspection/PosY6",0.),
#     ("PickAndPlace/MarkerX1",0.),
#     ("PickAndPlace/MarkerY1",0.),
#     ("PickAndPlace/MarkerX2",0.),
#     ("PickAndPlace/MarkerY2",0.),
#     ("AOI1/PosX1",0.),
#     ("AOI1/PosY1",0.),
#     ("AOI1/PosX2",0.),
#     ("AOI1/PosY2",0.),
#     ("AOI1/PosX3",0.),
#     ("AOI1/PosY3",0.),
#     ("AOI1/PosX4",0.),
#     ("AOI1/PosY4",0.),
#     ("AOI1/PosX5",0.),
#     ("AOI1/PosY5",0.),
#     ("AOI1/PosX6",0.),
#     ("AOI1/PosY6",0.),
#     ("Owen1/Temp1",0.),
#     ("Owen2/Temp2",0.),
#     ("Owen3/Temp3",0.),
#     ("AOI2/PosX1",0.),
#     ("AOI2/PosY1",0.),
#     ("AOI2/PosX2",0.),
#     ("AOI2/PosY2",0.),
#     ("AOI2/PosX3",0.),
#     ("AOI2/PosY3",0.),
#     ("AOI2/PosX4",0.),
#     ("AOI2/PosY4",0.),
#     ("AOI2/PosX5",0.),
#     ("AOI2/PosY5",0.),
#     ("AOI2/PosX6",0.),
#     ("AOI2/PosY6",0.),
#     ("Housing/HScrew",0.),
#     ("ConAssembly1-2/Con1-2Screw",0.),
#     ("PtAssembly1/Pt1Screw1",0.),
#     ("PtAssembly1/Pt1Screw2",0.),
#     ("PtAssembly2-3/Pt2",0.),
#     ("Welding/WeldFrequency",0.),
#     ("Label",None)
# ])

# reduce identical measurements to one feature
def reduce_measurements(identical_measurements, name):
    if name in identical_measurements:
        # print("REDUCE:", name, identical_measurements[name])
        return identical_measurements[name]
    # # parallel stations
    # if name == "ConAssembly1/Con1Screw" or name == "ConAssembly2/Con2Screw":
    #     return "ConAssembly1or2/Con1or2Screw"
    # if name == "PtAssembly2/Pt2" or name == "PtAssembly3/Pt2":
    #     return "PtAssembly2or3/Pt2or3"
    return name


# converts the result of the following query to python OrderedDict
# Query:
# select
#   begin.last.sv as type,
#   begin.bn as id,
#   entries.selectFrom(i=>new{n=i.last.n, v=i.last.v, u=i.last.u, t=i.bt}) as measurements,
#   String.valueOf(fin.last.bv) as label
# from pattern[ every begin=SenML(last.n='Source/ProdType') -> entries=SenML(begin.bn=bn) until fin=SenML(last.n='FunctionTest/Quality_OK' and begin.bn=bn)]
def Event2Dict(j, structure, complete=True):
    # features = copy.deepcopy(Features)
    features = OrderedDict()

    measurements = j['measurements']
    features['id'] = j['id']
    features['type'] = j['type']
    # print("Measurements: {}/{}".format(len(measurements), len(structure["measurements"])))

    if complete and len(structure["measurements"]) != len(measurements):
        raise Exception("Missing measurements: {} instead of {}\n missing {}".format(
            len(measurements),
            len(structure["measurements"]),
            validate(j, structure)))

    # TODO: optimize. Can I do this only once?
    for measurementID in structure["measurements"]:
        features[measurementID] = None

    for entry in measurements:
        feature_name = reduce_measurements(structure["identical_measurements"], entry['n'])
        features[feature_name] = entry['v']

    if 'label' in j:
        features['label'] = j['label']
    else:
        features['label'] = None

    # print(features)

    return features

def validate(j, structure):
    features = OrderedDict()
    for measurementID in structure["measurements"]:
        features[measurementID] = None
    for entry in j['measurements']:
        features[reduce_measurements(structure["identical_measurements"], entry['n'])] = True

    not_exist = []
    for feature, exist in features.items():
        if not exist:
            not_exist.append(feature)
    return not_exist

# converts ResultValue of json OGC-SensorThings to python OrderedDict
def SensorThings2Dict(j, complete=True):
    features = copy.deepcopy(Features)
    total = j['ResultValue']['total']
    if complete and total != 51:
        raise Exception("Total not 51.")
    #type = j['ResultValue']['type']['e'][0]['sv']
    #label = j['ResultValue']['label']['e'][0]['bv']
    #name = j['ResultValue']['label']['bn']
    measurements = j['ResultValue']['measurements']['e']
    features["Id"] = j['ResultValue']['type']['bn']
    features["Type"] = j['ResultValue']['type']['e'][0]['sv']

    if 'label' in j['ResultValue']:
        features["Label"] = j['ResultValue']['label']['e'][0]['bv']

    for entry in measurements:
        feature_name = reduce_measurements(entry['n'])
        features[feature_name] = entry['v']

    return features


