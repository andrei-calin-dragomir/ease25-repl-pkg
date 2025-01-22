import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from itertools import product
import statsmodels.api as sm
import scipy.stats as stats

# -- VISUALIZATION -- # 
sns.set(rc={"figure.dpi":300, 'savefig.dpi':300})
sns.set_style('white')

def show_barplot(df, metric, task="SA"):
    plt.figure(figsize=(6.5, 4.88))

    ax = sns.barplot(x='quantization_type', y=metric, hue='model', data=df)
    for container in ax.containers:
        ax.bar_label(container, fmt='%.3f') 

    plt.xlabel('Quantization')
    plt.ylabel('GPU Energy Consumption (J)')

    plt.savefig(f'{metric}_{task}_barplot.pdf')

    plt.show()

def show_barplots(df, metric, xlabel=""):
    # Set up the plot
    fig, axes = plt.subplots(1, 3, figsize=(13, 6), sharey=True)

    # Create subplots
    for i, variable in enumerate(df['task_name'].sort_values().unique()):
        sns.histplot(
            data=df[df['task_name'] == variable],
            x='quantization_type',
            weights=metric,
            hue='model',
            multiple='dodge',
            shrink=0.8,
            discrete=True,
            ax=axes[i]
        )

        axes[i].set_title(f'{variable}', fontsize=14)
        axes[i].tick_params(axis='x', rotation=45)

        for j, precision in enumerate(df['quantization_type'].sort_values().unique()):
            for z, model in enumerate(df['model'].unique()):

                mean_value = df[
                    (df['quantization_type'] == precision) & (df['model'] == model) & (df['task_name'] == variable)
                ][metric].mean()


                bar = axes[i].patches[j + 4 if model == 'LLaMA3' else j]

                axes[i].text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f'{mean_value:.2f}',
                    ha='center',
                    va='bottom'
                )

                axes[i].set_xlabel("")

    # Add dashed lines between subplots
    for i in range(1, 3):
        axes[i].spines['left'].set_visible(False)
        axes[i-1].spines['right'].set_visible(False)
        axes[i].yaxis.set_ticks_position('none')
        
        d = .015  # size of the dash
        kwargs = dict(transform=axes[i].transAxes, color='gray', clip_on=False)
        axes[i].plot((-d, +d), (-d, +d), **kwargs)
        axes[i].plot((-d, +d), (1-d, 1+d), **kwargs)
        kwargs.update(transform=axes[i-1].transAxes)
        axes[i-1].plot((1-d, 1+d), (-d, +d), **kwargs)
        axes[i-1].plot((1-d, 1+d), (1-d, 1+d), **kwargs)


    axes[1].get_legend().remove()
    axes[2].get_legend().remove()

    axes[0].set_ylabel('')

    fig.text(0.5, 0.015, 'Quantization', ha='center', va='center')

    plt.yscale('log')
    plt.tight_layout()
    plt.savefig(f'{metric}_barplot.pdf')
    plt.show()

def show_qqplots(data, metric):
    models = data['model'].unique()
    quantization = data['quantization_type'].unique() 
    tasks = data['task_name'].unique()

    for x, y, z in list(product(models, quantization, tasks)):
        print(x, y, z)
        group = data.loc[
            (data['model'] == x) & (data['quantization_type'] == y) & (data['task_name'] == z)
        ][metric]

        sm.qqplot(group, dist=stats.uniform, line='45')
        plt.title('Q-Q Plot')
        plt.show()

# -- Data Analysis -- 

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


def map_to_groups(data, fun, metric):
    rows = []
    stats = {}

    models = data['model'].unique()
    quantization = data['quantization_type'].unique() 
    tasks = data['task_name'].unique()

    for x, y, z in list(product(models, quantization, tasks)):

        group = data.loc[
            (data['model'] == x) & (data['quantization_type'] == y) & (data['task_name'] == z)
        ][metric]

        stats = fun(group)

        stats['model'] = x
        stats['quantization_type'] = y
        stats['task_name'] = z
        
        rows.append(stats)

    return pd.DataFrame(rows)

def map_to_tasks(data, fun, metric):
    stats = {}
    rows = []

    models = data['model'].unique()
    quantization = data['quantization_type'].sort_values().unique()
    tasks = data['task_name'].unique()

    for x, y in product(models, tasks):
        stats = {}
        samples = []

        for z in quantization:
            group = data.loc[
                (data['model'] == x) & (data['quantization_type'] == z) & (data['task_name'] == y)
            ][metric]

            samples.append(group.to_list())

        stats = fun(samples)
        stats['model'] = x
        stats['task_name'] = y 

        rows.append(stats)

    return pd.DataFrame(rows)


def compare_quantization(data, fun, metric):
    models = data['model'].unique()
    quantization = data['quantization_type'].sort_values().unique()
    tasks = data['task_name'].unique()

    stats = {}
    rows = []

    for x, y in product(models, tasks):
        for z in reversed(quantization):
            reference_group = data.loc[
                (data['model'] == x) & (data['quantization_type'] == z) & (data['task_name'] == y)
            ][metric]
            
            for k in list(set(quantization) - set(z)):
                stats = {}
                group = data.loc[
                    (data['model'] == x) & (data['quantization_type'] == k) & (data['task_name'] == y)
                ][metric]

                d, res = fun(reference_group, group)
                
                stats['model'] = x
                stats['task'] = y
                stats['reference'] = z
                stats['group'] = k
                stats['stat'] = d 
                stats['res'] = res 
                
                rows.append(stats)

    return pd.DataFrame(rows)
