from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from ..config import DATA_DIR
from ..models import FitnessLogRequest, FitnessLogResponse

router = APIRouter(prefix="/api/fitness", tags=["fitness"])


@router.post("/log", response_model=FitnessLogResponse)
def fitness_log(req: FitnessLogRequest):
    csv_dir = DATA_DIR / "fitness"
    csv_dir.mkdir(exist_ok=True)
    csv_path = csv_dir / f"{req.exercise}.csv"

    today = datetime.now().date().isoformat()

    lines = []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8") as file:
            lines = file.readlines()

    if lines and lines[-1].startswith(today):
        existing_sets = lines[-1].strip().split(',', 1)[1].strip('"')
        lines[-1] = f'{today},"{existing_sets},{req.sets}"\n'

        with csv_path.open("w", encoding="utf-8") as file:
            file.writelines(lines)
    else:
        if not csv_path.exists():
            csv_path.write_text('date,sets\n', encoding="utf-8")

        with csv_path.open("a", encoding="utf-8") as file:
            file.write(f'{today},"{req.sets}"\n')

    return FitnessLogResponse()
