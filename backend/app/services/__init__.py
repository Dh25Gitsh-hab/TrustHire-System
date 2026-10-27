"""
services — the "pipeline" steps that are not verification checks themselves:

  posting_fetcher    downloads a job posting from a URL and returns its text
  feature_extractor  pulls company name, domain, salary, e-mails ... out of text
  analyzer           runs the whole pipeline: fetch -> extract -> checks -> score
"""
