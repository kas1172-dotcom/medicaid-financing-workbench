"""
Validation layer: cross-checks analysis outputs against independent public sources.

Each check compares a workbench output to a second source and records:
  pass   : outputs agree within tolerance
  flag   : disagreement worth reviewing before publication
  data_unavailable: the second source file has not been uploaded yet

Results are included in dashboard_data.json and surfaced in the UI under
Data & Methods so a reader can see which findings have been independently
corroborated.
"""
