"""Statistical analysis module for the Linguistic Tax research toolkit (stub)."""


def load_experiment_data(db_path):
    raise NotImplementedError


def fit_glmm(df):
    raise NotImplementedError


def compute_bootstrap_cis(df, n_iterations=10000, seed=42):
    raise NotImplementedError


def run_mcnemar_analysis(df, baseline_condition="clean", model_filter=None, compare_interventions=False):
    raise NotImplementedError


def compute_kendall_tau(df):
    raise NotImplementedError


def apply_bh_correction(results_by_family, alpha=0.05):
    raise NotImplementedError


def run_sensitivity_analysis(df, drop_pct=0.10):
    raise NotImplementedError


def generate_effect_size_summary(glmm_results, kendall_results, bootstrap_results):
    raise NotImplementedError


def main():
    raise NotImplementedError
