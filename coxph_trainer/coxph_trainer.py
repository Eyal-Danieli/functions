# Copyright 2019 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Generated by nuclio.export.NuclioExporter

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

from mlrun.mlutils.data import get_sample, get_splits
from mlrun.mlutils.plots import gcf_clear

from mlrun.execution import MLClientCtx
from mlrun.datastore import DataItem
from mlrun.artifacts import PlotArtifact, TableArtifact

from cloudpickle import dumps
import pandas as pd
import os

from lifelines import CoxPHFitter, KaplanMeierFitter


def _coxph_log_model(
    context,
    model,
    dataset_key: str = "coxhazard-summary",
    models_dest: str = "models",
    plot_cov_groups: bool = False,
    p_value: float = 0.005,
    plot_key: str = "km-cx",
    plots_dest: str = "plots",
    file_ext="csv",
    extra_data: dict = {},
):
    """log a coxph model (and submodel locations)

    :param model:        estimated coxph model
    :param extra_data:   if this model wants to store the locations of submodels
                         use this
    """
    import matplotlib.pyplot as plt

    sumtbl = model.summary

    context.log_dataset(dataset_key, df=sumtbl, index=True, format=file_ext)

    model_bin = dumps(model)
    context.log_model(
        "cx-model",
        body=model_bin,
        artifact_path=os.path.join(context.artifact_path, models_dest),
        model_file="model.pkl",
    )
    if plot_cov_groups:
        select_covars = summary[summary.p <= p_value].index.values
        for group in select_covars:
            axs = model.plot_covariate_groups(group, values=[0, 1])
            for ix, ax in enumerate(axs):
                f = ax.get_figure()
                context.log_artifact(
                    PlotArtifact(f"cx-{group}-{ix}", body=plt.gcf()),
                    local_path=f"{plots_dest}/cx-{group}-{ix}.html",
                )
                gcf_clear(plt)


def _kaplan_meier_log_model(
    context,
    model,
    time_column: str = "tenure",
    dataset_key: str = "km-timelines",
    plot_key: str = "km-survival",
    plots_dest: str = "plots",
    models_dest: str = "models",
    file_ext: str = "csv",
):
    import matplotlib.pyplot as plt

    o = []
    for obj in model.__dict__.keys():
        if isinstance(model.__dict__[obj], pd.DataFrame):
            o.append(model.__dict__[obj])
    df = pd.concat(o, axis=1)
    df.index.name = time_column
    context.log_dataset(dataset_key, df=df, index=True, format=file_ext)
    model.plot()
    context.log_artifact(
        PlotArtifact(plot_key, body=plt.gcf()),
        local_path=f"{plots_dest}/{plot_key}.html",
    )
    context.log_model(
        "km-model",
        body=dumps(model),
        model_dir=f"{models_dest}/km",
        model_file="model.pkl",
    )


def train_model(
    context: MLClientCtx,
    dataset: DataItem,
    event_column: str = "labels",
    time_column: str = "tenure",
    encode_cols: dict = {},
    strata_cols: list = [],
    plot_cov_groups: bool = False,
    p_value: float = 0.005,
    sample: int = -1,
    test_size: float = 0.25,
    valid_size: float = 0.75,  # (after test removed)
    random_state: int = 1,
    models_dest: str = "",
    plots_dest: str = "",
    file_ext: str = "csv",
) -> None:
    """train models to predict the timing of events

    Although identical in structure to other training functions, this one
    requires generating a 'Y' that represents the age/duration/tenure of
    the obervation, designated 'tenure' here, and a binary labels columns that
    represents the event of interest, churned/not-churned.

    In addition, there is a strata_cols parameter, representing a list of
    stratification (aka grouping) variables.

    :param context:           the function context
    :param dataset:           ("data") name of raw data file
    :param event_column:      ground-truth (y) labels (considered as events in this model)
    :param time_column:       age or tenure column
    :param encode_cols:       dictionary of names and prefixes for columns that are
                              to hot be encoded.
    :param strata_cols:       columns used to stratify predictors
    :param plot_cov_groups:
    :param p_value:           (0.005) max p value for coeffcients selected
    :param sample:            Selects the first n rows, or select a sample
                              starting from the first. If negative <-1, select
                              a random sample
    :param test_size:         (0.25) test set size
    :param valid_size:        (0.75) Once the test set has been removed the
                              training set gets this proportion.
    :param random_state:      (1) sklearn rng seed
    :param models_dest:       destination subfolder for model artifacts
    :param plots_dest:        destination subfolder for plot artifacts
    :param file_ext:          format for test_set_key hold out data
    """
    from lifelines.plotting import plot_lifetimes
    import matplotlib.pyplot as plt

    models_dest = models_dest or "models"
    plots_dest = plots_dest or f"plots/{context.name}"

    raw, tenure, header = get_sample(dataset, sample, time_column)

    if encode_cols:
        raw = pd.get_dummies(
            raw,
            columns=list(encode_cols.keys()),
            prefix=list(encode_cols.values()),
            drop_first=True,
        )

    (xtrain, ytrain), (xvalid, yvalid), (xtest, ytest) = get_splits(
        raw, tenure, 3, test_size, valid_size, random_state
    )
    for X in [xtrain, xvalid, xtest]:
        drop_cols = X.columns.str.startswith(time_column)
        X.drop(X.columns[drop_cols], axis=1, inplace=True)
    for Y in [ytrain, yvalid, ytest]:
        Y.name = time_column

    context.log_dataset(
        "tenured-test-set",
        df=pd.concat([xtest, ytest.to_frame()], axis=1),
        format=file_ext,
        index=False,
    )

    km_model = KaplanMeierFitter().fit(ytrain, xtrain.labels)
    _kaplan_meier_log_model(context, km_model, models_dest=models_dest)

    coxdata = pd.concat([xtrain, ytrain.to_frame()], axis=1)
    cx_model = CoxPHFitter().fit(coxdata, time_column, event_column, strata=strata_cols)
    _coxph_log_model(
        context,
        cx_model,
        models_dest=models_dest,
        plot_cov_groups=plot_cov_groups,
        extra_data={"km": f"{models_dest}/km"},
    )
