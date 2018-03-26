class Controller:
    """Controller for the coordination of the optimization algorithm"""
    def __init__(self,name):
        logger.info("Initializing Optimization")
        self.name = name

    def getDirPath(self):
        project_dir = os.path.dirname(os.path.dirname(__file__))
        return project_dir

    def getDataPath(self):
        data_file = self.getDirPath() + '/data.dat'
        return data_file

    def startOpt(self):
        data_file=self.getDataPath()
        print(data_file)
        instance=model.create_instance('data.dat')
        instance.pprint()
        opt=SolverFactory("glpk")
        results=opt.solve(instance)
        return results