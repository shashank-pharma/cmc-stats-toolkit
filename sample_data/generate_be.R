# Regenerate the BE sample files (dummy data only) and print R's own results for them.
#
# Run from the repository root: Rscript sample_data/generate_be.R
# Base R only; the generator and analysis are the same as tests/golden/r/be_gold.R
# (lm(log(y) ~ sequence + subject + period + treatment), 90% confint, half-up rounding to
# 2 decimals; FDA (May 2026) I.B footnote 6; the half-up mode is a known limitation, URS-BE-020).
#
# Seed rule: for each file, the first seed from 1 upwards whose analysis gives the stated
# outcome for every parameter (all pass for the CV 20% file; overall BE fails for the CV 45%
# file), so each file shows what its name says. Writes one JSON line per file to
# be_r_output.jsonl (with R.version.string) and prints the same lines. The committed files
# were generated with R 4.6.1; R's default random number generator can change between
# releases, so another version may give different data (then rebuild expected.json).

out_dir <- "sample_data"
half_up <- function(x) floor(100 * x + 0.5) / 100

make_case <- function(seed, n_tr, n_rt, ratio, cv_w) {
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
      recs[[length(recs) + 1]] <- list(
        subject = subjects[i], sequence = seqs[i], period = p, treatment = trt,
        cmax = cmax, auc0t = round(auc_raw, 2),
        auc0inf = round(auc_raw * exp(runif(1, 0.02, 0.08)), 2)
      )
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
  ci <- 100 * exp(confint(fit, "treatmentT", level = 0.90))
  lo <- half_up(ci[1]); hi <- half_up(ci[2])
  counts <- table(d$sequence) / 2
  list(parameter = parameter, n_tr = as.integer(counts[["TR"]]), n_rt = as.integer(counts[["RT"]]),
       lo = lo, hi = hi, pass = lo >= 80 && hi <= 125)
}

cases <- list(
  list(file = "be_24_subjects_cv20.csv", n_tr = 12, n_rt = 12, ratio = 0.97, cv = 0.20,
       want_be = TRUE),
  list(file = "be_12_subjects_cv45.csv", n_tr = 6, n_rt = 6, ratio = 0.97, cv = 0.45,
       want_be = FALSE)
)

summary_lines <- character(0)
for (cs in cases) {
  for (seed in 1:1000) {
    recs <- make_case(seed, cs$n_tr, cs$n_rt, cs$ratio, cs$cv)
    res <- lapply(c("cmax", "auc0t", "auc0inf"), function(p) analyse(recs, p))
    be <- all(vapply(res, function(r) r$pass, TRUE))
    if (be == cs$want_be) break
  }
  lines <- c("subject,sequence,period,treatment,cmax,auc0t,auc0inf", vapply(recs, function(r)
    sprintf("%s,%s,%d,%s,%.2f,%.2f,%.2f", r$subject, r$sequence, as.integer(r$period),
            r$treatment, r$cmax, r$auc0t, r$auc0inf), ""))
  writeLines(lines, file.path(out_dir, cs$file))
  params <- paste(vapply(res, function(r) sprintf(
    "\"%s\": {\"n_tr\": %d, \"n_rt\": %d, \"ci_lower_rounded\": %.2f, \"ci_upper_rounded\": %.2f, \"within_limits\": %s}",
    r$parameter, r$n_tr, r$n_rt, r$lo, r$hi, tolower(as.character(r$pass))), ""), collapse = ", ")
  summary_lines <- c(summary_lines, sprintf(
    "{\"file\": \"%s\", \"seed\": %d, \"true_ratio\": %.2f, \"cv_within\": %.2f, \"r_version\": \"%s\", \"bioequivalent\": %s, \"parameters\": {%s}}",
    cs$file, seed, cs$ratio, cs$cv, R.version.string, tolower(as.character(be)), params))
}

# R's own results, read by build_expected.py (so building expected.json does not need R)
writeLines(summary_lines, file.path(out_dir, "be_r_output.jsonl"))
cat(summary_lines, sep = "\n")
