# Independent reference values for GOLD-DISS-001 (URS-DISS-002).
#
# Base R only; shares no code with cmc_stats.
# Run: Rscript tests/golden/r/dissolution_gold.R
# Prints one JSON object per case: inputs, expected values at the precision committed in the
# golden file (3 decimals, tolerance 0.001) and the full-precision values for the record.
#
# Method (FDA IR dissolution guidance (1997), section V.A, pp. 8-9), on mean profiles:
# - f1 = 100 * sum(|R - T|) / sum(R)
# - f2 = 50 * log10(100 / sqrt(1 + mean((R - T)^2)))

cases <- list(
  "GOLD-DISS-001" = list(
    reference = c(28, 52, 70, 82, 91),
    test = c(24, 47, 66, 79, 89)
  )
)

f1 <- function(r, t) 100 * sum(abs(r - t)) / sum(r)
f2 <- function(r, t) 50 * log10(100 / sqrt(1 + mean((r - t)^2)))
vec <- function(x) paste0("[", paste(sprintf("%g", x), collapse = ", "), "]")

for (id in names(cases)) {
  r <- cases[[id]]$reference
  t <- cases[[id]]$test
  cat(sprintf(paste0(
    "{\"id\": \"%s\", \"r_version\": \"%s\", ",
    "\"inputs\": {\"reference\": %s, \"test\": %s}, ",
    "\"expected\": {\"f2\": %.3f, \"f1\": %.3f}, ",
    "\"full_precision\": {\"f2\": %.9f, \"f1\": %.9f}}\n"),
    id, R.version.string, vec(r), vec(t), f2(r, t), f1(r, t), f2(r, t), f1(r, t)
  ))
}
