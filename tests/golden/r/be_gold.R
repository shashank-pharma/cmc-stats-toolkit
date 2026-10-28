# Independent reference values for GOLD-BE-001..003 (URS-BE-001 to 003, 012, 014, 016, 017).
#
# Base R only (set.seed, rnorm, lm, anova, confint, pt, qt); shares no code with cmc_stats.
# Run: Rscript tests/golden/r/be_gold.R
# Prints one JSON object per case: dummy input records and expected values, numbers to 8
# decimals.
#
# Dummy data: log-normal subject effect, period effect and within-subject error around a true
# T/R ratio, generated with set.seed() and rounded to 2 decimals BEFORE analysis, so the JSON
# input is exactly what was analysed.
#
# Method (2x2 crossover, ICH M13A (2024); FDA BE statistics guidance, as in ich-stats-rules):
# - lm(log(y) ~ sequence + subject + period + treatment); subject IDs are unique, so subject
#   is nested in sequence (type I anova: subject df = n - 2).
# - Treatment levels c("R", "T"): coefficient treatmentT = mean log T - mean log R.
# - 90% CI: confint(level = 0.90); PE and CI = 100 * exp(.).
# - TOST: p_lower = P(t > (d - ln 0.80) / se), p_upper = P(t < (d - ln 1.25) / se), df resid.
# - CVw = 100 * sqrt(exp(MSE) - 1).
# - Rounded limits: half up, floor(100 x + 0.5) / 100 (placeholder rule, pending confirmation
#   against the target agency text); these cases are far from the rounding boundary.

num <- function(x) sprintf("%.8f", x)
half_up <- function(x) floor(100 * x + 0.5) / 100

make_case <- function(seed, n_tr, n_rt, ratio, cv_w, with_inf) {
  set.seed(seed)
  n <- n_tr + n_rt
  subjects <- sprintf("S%02d", seq_len(n))
  seqs <- c(rep("TR", n_tr), rep("RT", n_rt))
  sd_w <- sqrt(log(cv_w^2 + 1))
  subj_eff <- rnorm(n, 0, 0.25)
  recs <- list()
  for (i in seq_len(n)) {
    for (p in 1:2) {
      trt <- if ((seqs[i] == "TR") == (p == 1)) "T" else "R"
      shift <- subj_eff[i] + (if (p == 2) 0.02 else 0) + (if (trt == "T") log(ratio) else 0)
      cmax <- round(exp(log(100) + shift + rnorm(1, 0, sd_w)), 2)
      auc_raw <- exp(log(1500) + shift + rnorm(1, 0, sd_w * 0.8))
      auc0t <- round(auc_raw, 2)
      auc0inf <- if (with_inf) round(auc_raw * exp(runif(1, 0.02, 0.08)), 2) else NA
      recs[[length(recs) + 1]] <- list(subject = subjects[i], sequence = seqs[i],
                                       period = p, treatment = trt,
                                       cmax = cmax, auc0t = auc0t, auc0inf = auc0inf)
    }
  }
  recs
}

analyse <- function(recs, parameter) {
  d <- data.frame(
    subject = factor(vapply(recs, function(r) r$subject, "")),
    sequence = factor(vapply(recs, function(r) r$sequence, ""), levels = c("TR", "RT")),
    period = factor(vapply(recs, function(r) r$period, 0)),
    treatment = factor(vapply(recs, function(r) r$treatment, ""), levels = c("R", "T")),
    y = vapply(recs, function(r) r[[parameter]], 0)
  )
  fit <- lm(log(y) ~ sequence + subject + period + treatment, data = d)
  a <- anova(fit)
  df <- fit$df.residual
  mse <- a["Residuals", "Mean Sq"]
  est <- unname(coef(fit)["treatmentT"])
  se <- summary(fit)$coefficients["treatmentT", "Std. Error"]
  ci <- 100 * exp(confint(fit, "treatmentT", level = 0.90))
  pe <- 100 * exp(est)
  p_lower <- pt((est - log(0.80)) / se, df, lower.tail = FALSE)
  p_upper <- pt((est - log(1.25)) / se, df)
  lo_r <- half_up(ci[1]); hi_r <- half_up(ci[2])
  terms <- c(sequence = "sequence", subject = "subject(sequence)", period = "period",
             treatment = "treatment", Residuals = "residual")
  anova_json <- paste(vapply(names(terms), function(t) sprintf(
    "{\"term\": \"%s\", \"df\": %d, \"ss\": %s, \"ms\": %s}",
    terms[[t]], as.integer(a[t, "Df"]), num(a[t, "Sum Sq"]), num(a[t, "Mean Sq"])
  ), ""), collapse = ", ")
  seq_counts <- table(d$sequence) / 2
  list(
    pass = lo_r >= 80 && hi_r <= 125,
    json = sprintf(paste0(
      "{\"parameter\": \"%s\", \"n_tr\": %d, \"n_rt\": %d, \"df\": %d, \"mse\": %s, ",
      "\"diff_log\": %s, \"se_log\": %s, \"t_value\": %s, \"pe_pct\": %s, ",
      "\"ci_lower_pct\": %s, \"ci_upper_pct\": %s, \"ci_lower_rounded\": %.2f, ",
      "\"ci_upper_rounded\": %.2f, \"within_limits\": %s, \"tost_p_lower\": %s, ",
      "\"tost_p_upper\": %s, \"cv_within_pct\": %s, \"anova\": [%s]}"),
      parameter, as.integer(seq_counts[["TR"]]), as.integer(seq_counts[["RT"]]), df,
      num(mse), num(est), num(se), num(qt(0.95, df)), num(pe), num(ci[1]), num(ci[2]),
      lo_r, hi_r, tolower(as.character(lo_r >= 80 && hi_r <= 125)), num(p_lower),
      num(p_upper), num(100 * sqrt(exp(mse) - 1)), anova_json
    )
  )
}

record_json <- function(r) {
  inf <- if (is.na(r$auc0inf)) "" else sprintf(", \"auc0inf\": %.2f", r$auc0inf)
  sprintf("{\"subject\": \"%s\", \"sequence\": \"%s\", \"period\": %d, \"treatment\": \"%s\", \"cmax\": %.2f, \"auc0t\": %.2f%s}",
          r$subject, r$sequence, as.integer(r$period), r$treatment, r$cmax, r$auc0t, inf)
}

# Seed for each case: the first seed from 1 upwards whose data fit the scenario with margin,
# so each case tests what its name says (random draws can land far from the true ratio):
# - 001 and 003 (BE): every parameter's 90% CI within 85.00-118.00
# - 002 (not BE): every parameter's 90% CI lower limit at or below 77.00
cases <- list(
  "GOLD-BE-001" = list(seed = 2, n_tr = 6, n_rt = 6, ratio = 0.98, cv_w = 0.15, inf = TRUE),
  "GOLD-BE-002" = list(seed = 1, n_tr = 6, n_rt = 6, ratio = 0.85, cv_w = 0.30, inf = TRUE),
  "GOLD-BE-003" = list(seed = 1, n_tr = 7, n_rt = 5, ratio = 1.02, cv_w = 0.12, inf = FALSE)
)

for (id in names(cases)) {
  cs <- cases[[id]]
  recs <- make_case(cs$seed, cs$n_tr, cs$n_rt, cs$ratio, cs$cv_w, cs$inf)
  params <- c("cmax", "auc0t", if (cs$inf) "auc0inf")
  results <- lapply(params, function(p) analyse(recs, p))
  be <- all(vapply(results, function(r) r$pass, TRUE))
  cat(sprintf(
    "{\"id\": \"%s\", \"r_version\": \"%s\", \"generator\": {\"seed\": %d, \"n_tr\": %d, \"n_rt\": %d, \"true_ratio\": %.2f, \"cv_within\": %.2f}, \"inputs\": {\"records\": [%s]}, \"expected\": {\"parameters\": [%s], \"bioequivalent\": %s}}\n",
    id, R.version.string, cs$seed, cs$n_tr, cs$n_rt, cs$ratio, cs$cv_w,
    paste(vapply(recs, record_json, ""), collapse = ", "),
    paste(vapply(results, function(r) r$json, ""), collapse = ", "),
    tolower(as.character(be))
  ))
}
