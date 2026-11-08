import unittest

from orbitlink.analytics.experiments import experiment_csv, run_parameter_sweep, summarize_experiment
from orbitlink.analytics.statistics import summarize


class ExperimentTests(unittest.TestCase):
    def test_statistics_include_percentile_variability_and_small_sample_ci(self):
        values = summarize([1, 2, 3, 4, 5])
        self.assertEqual(values["n"], 5)
        self.assertEqual(values["median"], 3)
        self.assertEqual(values["p95"], 5)
        self.assertGreater(values["sample_stddev"], 0)
        self.assertLess(values["ci95_low"], values["mean"])
        self.assertGreater(values["ci95_high"], values["mean"])
        single = summarize([42])
        self.assertIsNone(single["ci95_low"])

    def test_parameter_sweep_is_reproducible_and_exportable(self):
        kwargs = dict(parameter="altitude_km", values=[500, 550], repetitions=2,
                      duration_seconds=300, timestep_seconds=30)
        runs = run_parameter_sweep(**kwargs)
        self.assertEqual(len(runs), 4)
        self.assertEqual(runs, run_parameter_sweep(**kwargs))
        summary = summarize_experiment(runs)
        self.assertEqual(summary["500"]["availability_percent"]["n"], 2)
        self.assertIn("parameters_json", experiment_csv(runs).splitlines()[0])

    def test_invalid_sweep_parameter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "parameter"):
            run_parameter_sweep(parameter="throughput", values=[100])


if __name__ == "__main__":
    unittest.main()
