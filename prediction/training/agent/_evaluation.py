from sklearn import metrics

def print_metrics(expected, predicted):
    print("------------------------- EVALUATION -------------------------")
#     print("Accuracy Score: {}".format(metrics.accuracy_score(expected, predicted)))
#     print(metrics.classification_report(expected, predicted))
    print("Confusion Matrix:")
    print(metrics.confusion_matrix(expected, predicted))
#     print("Kappa Score: {}".format(metrics.cohen_kappa_score(expected, predicted)))
    print("Matthews Correlation Coefficient: {}".format(metrics.matthews_corrcoef(expected, predicted)))
    print("--------------------------------------------------------------")
#     plot_confusion_matrix(metrics.confusion_matrix(expected, predicted),classes=['Good','Faulty'],title='Confusion matrix',normalize=True)
#     plt.show()