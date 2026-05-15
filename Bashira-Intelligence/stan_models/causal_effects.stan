/*
 * Bashira Intelligence — Institutional-Grade Hierarchical Bayesian Delay Model
 * =============================================================================
 * Horseshoe prior for automatic relevance determination on fixed effects.
 * Partial pooling over Rig, Cluster, WellType, ProgressBand.
 * Student-t likelihood for heavy-tailed delay distributions.
 * LOO-CV log-likelihood for model comparison.
 * Posterior predictive draws for calibration checks.
 *
 * Authored: April 2026 | Engine: CmdStan via cmdstanpy
 */

data {
  int<lower=1> N;                           // number of observations
  int<lower=1> K;                           // number of fixed-effect features
  int<lower=1> R;                           // number of rigs
  int<lower=1> C;                           // number of clusters
  int<lower=1> W;                           // number of well types
  int<lower=1> B;                           // number of progress bands

  matrix[N, K] X;                           // feature matrix (standardized)
  vector[N] y;                              // target: schedule_delay_days

  array[N] int<lower=1, upper=R> rig_id;
  array[N] int<lower=1, upper=C> cluster_id;
  array[N] int<lower=1, upper=W> well_type_id;
  array[N] int<lower=1, upper=B> progress_band_id;
}

transformed data {
  real slab_scale = 3.0;                    // horseshoe slab width
  real slab_df = 4.0;                       // heavier tails on large effects
}

parameters {
  // ── Global intercept ──
  real alpha;

  // ── Horseshoe prior on fixed effects ──
  vector[K] beta_raw;
  vector<lower=0>[K] lambda;               // local shrinkage per feature
  real<lower=0> tau;                        // global shrinkage
  real<lower=0> c_sq;                       // slab regularization

  // ── Group effects (non-centered) ──
  vector[R] rig_raw;
  vector[C] cluster_raw;
  vector[W] well_type_raw;
  vector[B] progress_band_raw;

  // ── Scale parameters ──
  real<lower=0> sigma;                      // residual scale
  real<lower=0> sigma_rig;
  real<lower=0> sigma_cluster;
  real<lower=0> sigma_well_type;
  real<lower=0> sigma_progress_band;

  // ── Degrees of freedom for Student-t ──
  real<lower=2> nu;
}

transformed parameters {
  // ── Horseshoe: regularized shrinkage ──
  vector<lower=0>[K] lambda_tilde;
  vector[K] beta;

  for (k in 1:K) {
    lambda_tilde[k] = sqrt(
      c_sq * square(lambda[k]) / (c_sq + square(tau) * square(lambda[k]))
    );
  }
  beta = tau * lambda_tilde .* beta_raw;

  // ── Non-centered group effects ──
  vector[R] rig_effect = sigma_rig * rig_raw;
  vector[C] cluster_effect = sigma_cluster * cluster_raw;
  vector[W] well_type_effect = sigma_well_type * well_type_raw;
  vector[B] progress_band_effect = sigma_progress_band * progress_band_raw;

  // ── Linear predictor ──
  vector[N] mu = alpha + X * beta;
  for (n in 1:N) {
    mu[n] += rig_effect[rig_id[n]];
    mu[n] += cluster_effect[cluster_id[n]];
    mu[n] += well_type_effect[well_type_id[n]];
    mu[n] += progress_band_effect[progress_band_id[n]];
  }
}

model {
  // ── Intercept ──
  alpha ~ normal(0, 5);

  // ── Horseshoe priors ──
  beta_raw ~ std_normal();
  lambda ~ cauchy(0, 1);
  tau ~ cauchy(0, 1);
  c_sq ~ inv_gamma(0.5 * slab_df, 0.5 * slab_df * square(slab_scale));

  // ── Group random effects ──
  rig_raw ~ std_normal();
  cluster_raw ~ std_normal();
  well_type_raw ~ std_normal();
  progress_band_raw ~ std_normal();

  // ── Scale priors ──
  sigma ~ exponential(0.5);
  sigma_rig ~ exponential(1);
  sigma_cluster ~ exponential(1);
  sigma_well_type ~ exponential(1);
  sigma_progress_band ~ exponential(1);

  // ── Degrees of freedom ──
  nu ~ gamma(2, 0.1);

  // ── Likelihood: Student-t for robust estimation ──
  y ~ student_t(nu, mu, sigma);
}

generated quantities {
  // ── Posterior predictive draws ──
  vector[N] y_hat;
  for (n in 1:N) {
    y_hat[n] = student_t_rng(nu, mu[n], sigma);
  }

  // ── Log-likelihood for LOO-CV ──
  vector[N] log_lik;
  for (n in 1:N) {
    log_lik[n] = student_t_lpdf(y[n] | nu, mu[n], sigma);
  }

  // ── Horseshoe inclusion probabilities (shrinkage diagnostic) ──
  vector[K] kappa;
  for (k in 1:K) {
    kappa[k] = 1.0 - 1.0 / (1.0 + square(tau * lambda[k]));
  }
}
