import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from itertools import product
import statsmodels.api as sm
import scipy.stats as stats
from scipy.stats import shapiro, probplot, f_oneway, kruskal

# Clean and format columns to their expected value
def clean_and_format_df(df):
    # Columns with fixed names
    numeric_columns = [
        'cache-references', 'cache-misses', 'LLC-loads', 'LLC-load-misses', 
        'LLC-stores', 'LLC-store-misses', 'cache-misses_percent', 
        'LLC-load-misses_percent', 'LLC-store-misses_percent', 
        'DRAM_ENERGY (J)', 'PACKAGE_ENERGY (J)', 'PP0_ENERGY (J)', 
        'PP1_ENERGY (J)', 'TOTAL_MEMORY', 'TOTAL_SWAP', 'USED_MEMORY', 
        'USED_SWAP', 'execution_time', 'PROCESS_CPU_USAGE', 
        'PROCESS_MEMORY', 'PROCESS_VIRTUAL_MEMORY'
    ]

    # Add dynamic columns based on regex
    cpu_columns = df.columns[df.columns.str.match(r'^CPU_USAGE_\d+$') | df.columns.str.match(r'^CPU_FREQUENCY_\d+$')].tolist()
    numeric_columns.extend(cpu_columns)

    # Convert columns to numeric
    for column in numeric_columns:
        if column in df.columns:  # Check if the column exists in the DataFrame
            df[column] = pd.to_numeric(df[column], errors='coerce')

def plot_qq_grid(df : pd.DataFrame, metric, dist='norm', figsize=(32, 21)):
    # Create the figure and axes
    fig, axes = plt.subplots(len(df['subject'].unique()), len(df['target'].unique()), figsize=figsize)
    fig.tight_layout(pad=5.0)

    for row, subject in enumerate(df['subject'].unique()):
        for col, target in enumerate(df['target'].unique()):
            ax = axes[row, col]
            
            # Extract the data for the current subject and target function
            subject_data = df[(df['subject'] == subject) & (df['target'] == target)][metric]

            if len(subject_data) > 0:
                # Generate theoretical quantiles and ordered data
                probplot(subject_data, dist=dist, plot=ax)

                # Add a title for the plot
                ax.set_title(f"Subject : {subject}, Target : {target}", fontsize=8)
                ax.tick_params(axis='both', which='major', labelsize=6)

            else:
                ax.text(0.5, 0.5, "No Data", ha='center', va='center', fontsize=8)
                ax.set_xticks([])
                ax.set_yticks([])

    # Set global labels
    fig.suptitle(f"Q-Q Plots for {metric}: Subjects and Target Pairs", fontsize=16)
    plt.show()


def remove_outliers(data, column, threshold=1):
    threshold = threshold 
    data = data[data[column] >= 0]
    z_scores = np.abs(
        (data[column] - data[column].mean()) / data[column].std()
    )
    # dataframe with data and the zscores
    data_with_zscores = pd.concat(
        [data, z_scores], axis=1, #keys=[data.name, 'zscores']
    )
    # filters the rows having z scores greater than the threshold 
    # returns a pd.Series with data filtered according to the z_scores
    return data[z_scores < threshold]
    #return data.where(z_scores < threshold, np.nan)

def get_rows_by_subject_target(df, x, y):
    return df.loc[(df['subject'] == x) & (df['target'] == y)]
