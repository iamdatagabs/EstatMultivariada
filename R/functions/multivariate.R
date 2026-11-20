# Reusable multivariate analysis helpers
# Original course scripts remain at repository root as historical references.

validate_multivariate_data <- function(data, min_rows = 3, min_numeric = 2) {
  stopifnot(is.data.frame(data))
  numeric_data <- data[vapply(data, is.numeric, logical(1))]
  if (nrow(data) < min_rows) stop("Insufficient rows for multivariate analysis.")
  if (ncol(numeric_data) < min_numeric) stop("Insufficient numeric variables.")
  if (anyDuplicated(names(data))) stop("Column names must be unique.")
  invisible(TRUE)
}

run_pca <- function(data, scale = TRUE) {
  validate_multivariate_data(data)
  numeric_data <- data[vapply(data, is.numeric, logical(1))]
  stats::prcomp(numeric_data, center = TRUE, scale. = scale)
}

run_hierarchical_clustering <- function(data, method = "ward.D2", distance = "euclidean") {
  validate_multivariate_data(data)
  numeric_data <- data[vapply(data, is.numeric, logical(1))]
  scaled <- scale(numeric_data)
  stats::hclust(stats::dist(scaled, method = distance), method = method)
}
