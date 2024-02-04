import pandas as pd
import numpy as np

"""
This modules contains methods for clustering binary factors in an unannotated dataset based on 
different clustering strategies

1. Corr - correlations 
2. Voting 
3. Random 
4. Random with undecided (i.e. this will discard some factors from the decision making process)

Each of these functions receives a dataframe with a set of factors marked with true and false
if they contribute to the row's argument and a decision column. 

Each function returns a dictionary of column names and their assigned polarity (pi, delta, or undecided), 
where pi is strictly opposing to delta and undecided is the neutral case (and does not contribute to any 
argument in this casebase). 
"""


def cluster_factors_corr(df, y_name):
    """
    Clusters the factors (column names) in the dataset by the correlation of
    columns with a certain outcome
    Returns: a dictionary of factor names and their polarities clustered using correlations
    NaN - value only present in one of the rows
    """
    # take the correlations with y
    cor_dict = zip(df.columns, df.corr()[y_name].astype(float))
    factors = {key: "pi" if value > 0.1 else ("delta" if value < -0.1 else "un") for key, value in cor_dict}
    factors.pop(y_name)
    return factors


def cluster_factors_voting(df, y_name):
    """
    Clusters the factors (column names) in the dataset with a voting mechanism,
    where a factor which appears in the dataset with a certain outcome more times is assigned that polarity.
    Returns: a dictionary of factor names and their polarities clustered using voting.

    The dataframe needs to be balanced between the two classes, otherwise this will favour the more prominent class.
    """
    true_votes = {column: ((df[column] == True) & (df[y_name] == True)).sum() for column in df.columns}
    false_votes = {column: ((df[column] == True) & (df[y_name] == False)).sum() for column in df.columns}

    factors = {key: "pi" if value > false_votes[key] else ("un" if value == false_votes[key] else "delta")
               for key, value in true_votes.items()}

    factors.pop(y_name)
    return factors


def cluster_factors_rand(df, y_name):
    """
    Clusters the factors (column names) in the dataset with random polarities, not including undecided
    Returns: a dictionary of factor names and their randomly assigned polarities.
    """
    np.random.seed(42)  # Set a seed for reproducibility
    polarities = np.random.choice(["pi", "delta"], size=len(df.columns))
    factors = {column: polarity for column, polarity in zip(df.columns, polarities)}
    factors.pop(y_name)

    return factors


def cluster_factors_rand_un(df, y_name):
    """
    Clusters the factors (column names) in the dataset with random polarities with undecided.
    Returns: a dictionary of factor names and their randomly assigned polarities.
    """
    np.random.seed(42)  # Set a seed for reproducibility
    polarities = np.random.choice(["pi", "delta", "un"], size=len(df.columns))
    factors = {column: polarity for column, polarity in zip(df.columns, polarities)}
    factors.pop(y_name)

    return factors
