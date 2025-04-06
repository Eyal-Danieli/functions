from mlrun.model_monitoring.applications import (
    ModelMonitoringApplicationBase,
    ModelMonitoringApplicationResult,
)
from mlrun.common.schemas.model_monitoring.constants import (
    ResultKindApp,
    ResultStatusApp,
)

import mlrun.model_monitoring.applications.context as mm_context
import mlrun.model_monitoring.applications.results as mm_results
class DemoMonitoringApp(ModelMonitoringApplicationBase):
    NAME = "monitoring-test"

    # noinspection PyMethodOverriding
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__()

    def do_tracking(
        self, monitoring_context: mm_context.MonitoringApplicationContext
    ) -> list[mm_results.ModelMonitoringApplicationResult]:
        monitoring_context.nuclio_logger.info("Running demo app")

        monitoring_context.nuclio_logger.info("Asserted sample_df length")
        monitoring_context.logger.info(
            "Now with MLRun logger", sample_df_len=len(monitoring_context.sample_df)
        )
        return [
            ModelMonitoringApplicationResult(
                name="data_drift_test",
                value=2.15,
                kind=ResultKindApp.data_drift,
                status=ResultStatusApp.detected,
            ),
            ModelMonitoringApplicationResult(
                name="model_perf",
                value=80,
                kind=ResultKindApp.model_performance,
                status=ResultStatusApp.no_detection,
            ),
        ]