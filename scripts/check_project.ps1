$ErrorActionPreference = "Stop"

Write-Host "Checking ABC Quant project..."
python -m pytest
Write-Host "Done."
