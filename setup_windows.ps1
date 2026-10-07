# One-time setup. In PowerShell, from the pin-studio folder:  .\setup_windows.ps1
# If scripts are blocked first run:  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env - open it in Notepad and paste your OpenAI key." }
Write-Host "Done. Start the app with:  streamlit run app.py"
