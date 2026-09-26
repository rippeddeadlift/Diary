import subprocess
import sys
from pathlib import Path

def ensure_dependencies():
    """Prüft die requirements.txt und installiert fehlende Pakete."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    if requirements_file.exists():
        try:
            # -q sorgt für eine weniger geschwätzige Ausgabe (quiet)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(requirements_file)])
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Abhängigkeiten: {e}")

if __name__ == "__main__":
    ensure_dependencies()
    # Hier folgt der eigentliche Start des Servers, z.B.:
    # import uvicorn
    # uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)