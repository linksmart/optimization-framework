
""" Random Forest """
def random_forest(params):
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(n_estimators=100,  class_weight={0:1.0, 1:0.05}, max_depth=90, n_jobs=4)

""" Gradient Boosting """
def gradient_boosting(params):
    from sklearn.ensemble import GradientBoostingClassifier
    losses = ['deviance', 'exponential']
    return GradientBoostingClassifier(loss=losses[1], n_estimators=100, max_depth=90, learning_rate=0.1)