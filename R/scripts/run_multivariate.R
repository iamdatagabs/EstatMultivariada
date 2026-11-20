args <- commandArgs(trailingOnly = TRUE)
input <- if (length(args) >= 1) args[[1]] else "data/raw/Euroemp.csv"
output <- if (length(args) >= 2) args[[2]] else "data/gold/r_multivariate"
dir.create(output, recursive = TRUE, showWarnings = FALSE)
source("R/functions/multivariate.R")
data <- read.csv(input, check.names = TRUE)
fit <- run_pca(data)
write.csv(fit$x, file.path(output, "pca_scores.csv"), row.names = FALSE)
write.csv(fit$rotation, file.path(output, "pca_loadings.csv"))
write.csv(summary(fit)$importance, file.path(output, "pca_variance.csv"))
