# Independent reference values for GOLD-STAB-001..003 (URS-STAB-001 to 005, 008).
#
# Base R only (lm, anova, predict, qt, uniroot); shares no code with cmc_stats.
# Run: Rscript tests/golden/r/stability_gold.R
# Prints one JSON object per case: inputs and expected values, numbers to 8 decimals.
#
# Method (ICH Q1E, as set out in the ich-stats-rules skill):
# - Slopes: anova(common, full), F on the full model's residual error.
# - Intercepts (only if slope p >= 0.25): anova(pooled, common), F on the common-slope model's
#   residual error (sequential ANCOVA).
# - Model: both p >= 0.25 -> pooled; slopes equal only -> common slope; else separate per-batch
#   lm fits, each with its own residual error (df = n - 2): ICH Q1E Appendix B.1 per batch,
#   provisional, pending confirmation against the Q1E text. Not the full-model pooled error.
# - One-sided 95% lower bound of the mean = lower limit of the two-sided 90% confidence interval
#   from predict(..., interval = "confidence", level = 0.90).
# - Crossing: earliest t >= 0 where the bound meets the limit (grid scan, then uniroot).
# - X = shortest of the batches' last time points; cap = min(2X, X + 12) (ICH Q1E Appendix A,
#   statistical analysis performed). Shelf-life = floor(min(crossing, cap)).

alpha <- 0.25
limit <- 95.0
times <- c(0, 3, 6, 9, 12, 18, 24)
common_batches <- list(
  B001 = c(99.9, 99.7, 99.5, 98.6, 98.6, 97.6, 96.6),
  B002 = c(100.5, 99.8, 99.0, 98.9, 98.5, 97.5, 96.9)
)
cases <- list(
  "GOLD-STAB-001" = c(100.1, 99.8, 99.5, 98.7, 98.5, 97.5, 96.8),
  "GOLD-STAB-002" = c(99.4, 99.1, 98.8, 98.0, 97.8, 96.8, 96.1),
  "GOLD-STAB-003" = c(100.1, 99.6, 99.1, 98.2, 97.8, 96.4, 95.4)
)

num <- function(x) if (is.na(x)) "null" else sprintf("%.8f", x)
vec <- function(x) paste0("[", paste(sprintf("%.1f", x), collapse = ", "), "]")
str <- function(x) if (is.na(x)) "null" else paste0("\"", x, "\"")

crossing <- function(bound) {
  g <- function(t) bound(t) - limit
  if (g(0) <= 0) return(0)
  grid <- seq(0, 600, by = 0.05)
  below <- which(vapply(grid, g, numeric(1)) <= 0)
  if (length(below) == 0) return(NA_real_)
  i <- below[1]
  uniroot(g, c(grid[i - 1], grid[i]), tol = 1e-12)$root
}

lwr <- function(fit, newdata) {
  predict(fit, newdata = newdata, interval = "confidence", level = 0.90)[, "lwr"]
}

analyse <- function(id, b003) {
  batches <- c(common_batches, list(B003 = b003))
  labels <- names(batches)
  d <- data.frame(
    batch = factor(rep(labels, each = length(times)), levels = labels),
    time = rep(times, length(labels)),
    y = unlist(batches, use.names = FALSE)
  )
  full <- lm(y ~ batch * time, data = d)
  common <- lm(y ~ batch + time, data = d)
  pooled <- lm(y ~ time, data = d)

  a_slope <- anova(common, full)
  slope_p <- a_slope$`Pr(>F)`[2]
  int <- list(F = NA, df_num = NA, df_den = NA, p = NA)
  if (slope_p >= alpha) {
    a_int <- anova(pooled, common)
    int <- list(F = a_int$F[2], df_num = a_int$Df[2], df_den = a_int$Res.Df[2],
                p = a_int$`Pr(>F)`[2])
  }
  model <- if (slope_p < alpha) "separate" else if (int$p < alpha) "common_slope" else "pooled"

  # Per-batch least-squares fits (URS-STAB-001)
  fits <- vapply(labels, function(b) {
    f <- lm(y ~ time, data = d[d$batch == b, ])
    s <- summary(f)
    sprintf(
      "{\"label\": %s, \"intercept\": %s, \"slope\": %s, \"intercept_se\": %s, \"slope_se\": %s, \"residual_df\": %d, \"mse\": %s}",
      str(b), num(coef(f)[1]), num(coef(f)[2]), num(s$coefficients[1, 2]),
      num(s$coefficients[2, 2]), f$df.residual, num(s$sigma^2)
    )
  }, character(1))

  # Lines whose bound decides the shelf-life
  lines <- list()
  if (model == "pooled") {
    lines[["pooled"]] <- list(fit = pooled, nd = function(t) data.frame(time = t), label = NA)
  } else if (model == "common_slope") {
    for (b in labels) {
      lines[[b]] <- local({
        bb <- b
        list(fit = common, label = bb,
             nd = function(t) data.frame(batch = factor(bb, levels = labels), time = t))
      })
    }
  } else {
    for (b in labels) {
      lines[[b]] <- local({
        bb <- b
        list(fit = lm(y ~ time, data = d[d$batch == bb, ]), label = bb,
             nd = function(t) data.frame(time = t))
      })
    }
  }
  per_line <- lapply(lines, function(l) {
    bound <- function(t) lwr(l$fit, l$nd(t))
    cf <- predict(l$fit, newdata = l$nd(c(0, 1)))
    list(label = l$label, intercept = cf[1], slope = cf[2] - cf[1],
         df = l$fit$df.residual, t_value = qt(0.95, l$fit$df.residual),
         bound_at_0 = bound(0), crossing = crossing(bound))
  })
  crossings <- vapply(per_line, function(p) p$crossing, numeric(1))
  gov <- if (model == "pooled") NA else per_line[[which.min(crossings)]]$label
  crossing_min <- min(crossings, na.rm = TRUE)

  x <- min(vapply(batches, function(v) max(times), numeric(1)))
  cap <- min(2 * x, x + 12)
  shelf <- floor(min(crossing_min, cap))

  per_json <- vapply(per_line, function(p) sprintf(
    "{\"label\": %s, \"intercept\": %s, \"slope\": %s, \"df\": %d, \"t_value\": %s, \"bound_at_0\": %s, \"crossing_months\": %s}",
    str(p$label), num(p$intercept), num(p$slope), p$df, num(p$t_value),
    num(p$bound_at_0), num(p$crossing)
  ), character(1))

  inputs <- sprintf(
    "{\"lower_limit\": %.1f, \"batches\": [%s]}", limit,
    paste(vapply(labels, function(b) sprintf(
      "{\"label\": \"%s\", \"times_months\": %s, \"values\": %s}",
      b, vec(times), vec(batches[[b]])
    ), character(1)), collapse = ", ")
  )
  expected <- sprintf(paste0(
    "{\"model\": %s, ",
    "\"slopes\": {\"F\": %s, \"df_num\": %d, \"df_den\": %d, \"p\": %s}, ",
    "\"intercepts\": %s, ",
    "\"batch_fits\": [%s], ",
    "\"per_batch\": [%s], ",
    "\"governing_batch\": %s, \"crossing_months\": %s, ",
    "\"x_months\": %s, \"cap_months\": %s, \"proposed_shelf_life_months\": %d}"),
    str(model), num(a_slope$F[2]), a_slope$Df[2], a_slope$Res.Df[2], num(slope_p),
    if (is.na(int$p)) "null" else sprintf(
      "{\"F\": %s, \"df_num\": %d, \"df_den\": %d, \"p\": %s}",
      num(int$F), int$df_num, int$df_den, num(int$p)),
    paste(fits, collapse = ", "), paste(per_json, collapse = ", "),
    str(gov), num(crossing_min), num(x), num(cap), as.integer(shelf)
  )
  sprintf("{\"id\": \"%s\", \"r_version\": \"%s\", \"inputs\": %s, \"expected\": %s}",
          id, R.version.string, inputs, expected)
}

for (id in names(cases)) cat(analyse(id, cases[[id]]), "\n")
