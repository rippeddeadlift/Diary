# Server Tests ausführen

## Windows PowerShell

### Option 1: Mit virtuellem Environment (empfohlen)

```powershell
# 1. Virtual Environment erstellen (falls noch nicht vorhanden)
python -m venv server\.venv

# 2. Virtual Environment aktivieren
.\server\.venv\Scripts\Activate.ps1

# 3. Dependencies installieren
pip install -r server\requirements.txt

# 4. Tests ausführen
pytest

# Oder mit Python-Modul:
python -m pytest
```

### Option 2: Ohne Virtual Environment (nicht empfohlen)

```powershell
# Dependencies installieren
pip install -r server\requirements.txt

# Tests ausführen
python -m pytest
```

## Alle Tests ausführen

```powershell
pytest -v
```

## Spezifische Test-Datei

```powershell
pytest tests/test_photos_repo.py -v
```

## Einzelnen Test ausführen

```powershell
pytest tests/test_photos_repo.py::TestSafeName::test_normal_name -v
```

## Mit Coverage

```powershell
pytest --cov=server --cov-report=html
```

## Troubleshooting

Falls `pytest` nicht gefunden wird:
- Verwende `python -m pytest` statt `pytest`
- Stelle sicher, dass das Virtual Environment aktiviert ist
- Prüfe, ob alle Dependencies installiert sind: `pip list | findstr pytest`
