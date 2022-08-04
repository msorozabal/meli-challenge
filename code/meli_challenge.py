# -*- coding: utf-8 -*-
"""meli-challenge.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RrpljTPL0bWLXuGicgLnG1oDp4fWHIhp

### Read Dataset
"""

!unzip MLA_100k_checked_v3.jsonlines.zip

!pip install catboost

import json
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import balanced_accuracy_score, recall_score, precision_score, f1_score, accuracy_score
from sklearn.metrics import precision_recall_curve, average_precision_score, confusion_matrix
from sklearn.metrics import roc_curve, roc_auc_score, RocCurveDisplay

from catboost import CatBoostClassifier
from sklearn import metrics


# You can safely assume that `build_dataset` is correctly implemented
def build_dataset():
    data = [json.loads(x) for x in open("MLA_100k_checked_v3.jsonlines")]
    target = lambda x: x.get("condition")
    N = -10000
    X_train = data[:N]
    X_test = data[N:]
    y_train = [target(x) for x in X_train]
    y_test = [target(x) for x in X_test]
    for x in X_test:
        del x["condition"]
    return X_train, y_train, X_test, y_test

X_train, y_train, X_test, y_test = build_dataset()

X_train[0]

# first we parse the json in a nested dataframe, to convert dicts into new colums i.e -> seller_address TRANSFORM INTO seller_address_city, seller_address_country_name, etc.. 

from pandas.io.json._normalize import nested_to_record    

flat_Train = nested_to_record(X_train, sep='_')
X_train = pd.DataFrame(flat_Train)
print(f'X_train shape {X_train.shape}')


flat_Test = nested_to_record(X_test, sep='_')
X_test = pd.DataFrame(flat_Test)
print(f'X_test shape {X_test.shape}')

# first row 
X_train.head(1).T

#convert target labels to DF and encode {new = 0, used = 1}

y_train = pd.DataFrame(y_train, columns = ['label'])
y_train = y_train.replace('used', 1)
y_train = y_train.replace('new', 0)

y_test = pd.DataFrame(y_test, columns = ['label'])
y_test = y_test.replace('used', 1)
y_test = y_test.replace('new', 0)

"""### First we are see the distribution of the target labels to understand if it's a unbalanced dataset problem and a brief describe about our data in X

#### Train label distribution
"""

sns.countplot(data = y_train, x = 'label')

print(f'%PERCENT: \n{np.round(y_train.label.value_counts(normalize = True),2)} \n')
print(f'#QTY: \n{np.round(y_train.label.value_counts(),2)}')

"""#### X_train distribution"""

pd.set_option('display.float_format',lambda x:'%.3f'% x) #remove scientific notation

X_train.describe()

# if the mean price arround in 60k maybe we have some outliers on the price column, then we replace with the mean.

X_train['price'].where(X_train['price'] > 4000000).value_counts()

X_train.loc[X_train.price > 4000000, 'price'] = X_train['price'].mean()



sns.displot(
  data=X_train,
  x="price",
  kind="hist",
  aspect=1.4,
  log_scale=10,
  bins=10
)

"""#### Test label distribution"""

sns.countplot(data = y_test, x = 'label')

print(f'%PERCENT: \n{np.round(y_test.label.value_counts(normalize = True),2)} \n')
print(f'#QTY: \n{np.round(y_test.label.value_counts(),2)}')

"""#### X_test distribution"""

X_test.describe()

sns.displot(
  data=X_test,
  x="price",
  kind="hist",
  aspect=1.4,
  log_scale=10,
  bins=10
)

"""## EDA """

quantitative_vars = X_train.select_dtypes(include=['int64', 'float64']).columns
categorical_features = X_train.select_dtypes(include=['object']).columns

for col in quantitative_vars:
    print(col,':')
    print(X_train[col].value_counts(), '\n')

numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns

#scaler

scaler = StandardScaler()
scaler.fit(X_train[numeric_features])
X_train[numeric_features]  = scaler.transform(X_train[numeric_features])

X_test[numeric_features] = scaler.transform(X_test[numeric_features])

X_train = X_train.fillna(0)
X_test = X_test.fillna(0)

cols_common = [X_train.columns[i] for i in range(len(X_train.columns))]

"""## Feature Correlations"""

plt.figure(figsize = (25,10))

sns.heatmap(X_train[cols_common].corr().round(2),
            vmin = -1,
            vmax = 1,
            annot = True,
            cmap = 'RdBu')

plt.savefig(f'correlations.jpg')
plt.show()

# Drop columns with object-list into cell. In a second version we parse this fields to enrich the model.

X_train.drop(['condition', 'shipping_tags', 'shipping_methods', 'pictures', 'descriptions', 'coverage_areas', 'sub_status',
              'deal_ids','non_mercado_pago_payment_methods','variations','attributes','tags','shipping_free_methods'], axis=1, inplace=True)

X_test.drop(['shipping_tags', 'shipping_methods', 'pictures', 'descriptions', 'coverage_areas', 'sub_status',
              'deal_ids','non_mercado_pago_payment_methods','variations','attributes','tags','shipping_free_methods'], axis=1, inplace=True)

"""## Model Train"""

catboost_params = {'iterations': 300,
        'learning_rate': 0.1,
        'eval_metric': 'F1',
        'l2_leaf_reg': 0.5,
        'use_best_model':True,
        'early_stopping_rounds':30,
        "loss_function": "Logloss",
        }

model = CatBoostClassifier(**catboost_params, random_state = 0)

X_train_2_sorted = X_train.reindex(columns = sorted(X_train.columns))
X_test_2_sorted = X_test.reindex(columns = sorted(X_test.columns))

categorical_features_indices = np.where(X_train_2_sorted.dtypes != float)[0]

model.fit(X_train_2_sorted,
          y_train, 
          cat_features=categorical_features_indices,
          eval_set=(X_test_2_sorted, y_test),
          plot=True
          #verbose = False
          )



sorted_feature_importance = model.feature_importances_.argsort()

plt.figure(figsize = (10,13))
plt.barh(X_train_2_sorted.columns[sorted_feature_importance],
        model.feature_importances_[sorted_feature_importance], 
        color='purple')

plt.xlabel("Model Feature Importance")



"""## Model Evaluation"""

from sklearn.metrics import (confusion_matrix, precision_recall_curve, auc,
                             roc_curve, recall_score, classification_report, f1_score,
                             precision_recall_fscore_support)

predictions_probs = model.predict_proba(X_test_2_sorted)

# Print metrics
print("Classification report")

test_pred = np.argmax(predictions_probs, axis=1)

print(classification_report(y_test, test_pred, target_names=list(map(lambda x: str(x),np.unique(y_test)))))

print("Confusion matrix")
print(metrics.confusion_matrix(y_test, test_pred))
print("")

# Precision - Recall 

def plot_prec_recall_vs_tresh(precision, recall, threshold):
    
    plt.plot(threshold, precision[:-1], 'b--', label='precision')
    plt.plot(threshold, recall[:-1], 'g--', label = 'recall')
    plt.xlabel('Threshold')
    plt.legend()
    
    return plt.figure()


precision, recall, threshold = precision_recall_curve(y_test, predictions_probs[:,1])

fig = plot_prec_recall_vs_tresh(precision, recall, threshold)
plt.show(fig)

## ROC AUC

fpr, tpr, _ = roc_curve(y_test, predictions_probs[:,1])

roc_display = RocCurveDisplay(fpr=fpr, tpr=tpr).plot()

print(f"AUC: {roc_auc_score(y_test, predictions_probs[:,1])}")



"""## Hyperparameter Optimization"""

grid = {'iterations': [200, 300, 400],
        'learning_rate': [0.05, 0.1, 0.2],
        'depth': [2, 4, 6],
        'l2_leaf_reg': [0.2, 0.5, 1]}

search = GridSearchCV(model, grid)

search.fit(X_train_2_sorted, 
           y_train, 
           eval_set=(X_test_2_sorted, y_test),
           plot = True, 
           verbose = False,
           cat_features=categorical_features_indices)

print(" Results from Grid Search " )
print("\n The best estimator across ALL searched params:\n",search.best_estimator_)
print("\n The best score across ALL searched params:\n",search.best_score_)
print("\n The best parameters across ALL searched params:\n",search.best_params_)



"""## Export the Model """

from joblib import dump, load
dump(model, 'MeLi-challenge-20220628.joblib')

from google.colab import drive

drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# %%shell
# jupyter nbconvert --to html ///content/meli_challenge.ipynb

