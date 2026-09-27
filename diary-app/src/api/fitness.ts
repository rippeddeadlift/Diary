import { loadSetsCsv, type SetsRow } from '@/data/setsCsv'

export type Exercise = 'dips' | 'pullups'

const CSV_PATHS: Record<Exercise, string> = {
  dips: '/fitness/dips.csv',
  pullups: '/fitness/pullups.csv',
}

export async function loadExerciseRows(exercise: Exercise): Promise<SetsRow[]> {
  return loadSetsCsv(CSV_PATHS[exercise])
}

export async function logFitnessSet(exercise: Exercise, sets: string): Promise<void> {
  const trimmed = sets.trim()
  if (!trimmed) throw new Error('Keine Sets angegeben')

  const res = await fetch('/api/fitness/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ exercise, sets: trimmed }),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || `${res.status} ${res.statusText}`)
  }
}
