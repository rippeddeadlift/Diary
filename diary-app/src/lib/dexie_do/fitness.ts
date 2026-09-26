import { getTodayISO, loadSetsCsv } from '@/data/setsCsv'; // Deine bestehende Funktion nutzen!
import { db } from './schema';

export interface FitnessEntry {
  id?: number;
  date: string;
  exercise: 'dips' | 'pullups';
  sets: string;
  synced: 0 | 1;
}

export const syncFromCSV = async () => {
  const paths = [
    { exercise: 'dips' as const, path: '/fitness/dips.csv' },
    { exercise: 'pullups' as const, path: '/fitness/pullups.csv' }
  ];

  for (const { exercise, path } of paths) {
    try {
      const csvData = await loadSetsCsv(path); 
      await db.transaction('rw', db.fitnessLogs, async () => {
        for (const row of csvData) {
          const setsString = row.sets.join(','); // Wandelt [1, 3, 6] in "1,3,6" um
          const existing = await db.fitnessLogs.where({ date: row.date, exercise }).first();
          if (!existing) {
            await db.fitnessLogs.add({ date: row.date, exercise, sets: setsString, synced: 1 });
          } else if (existing.synced === 1) {
            await db.fitnessLogs.update(existing.id!, { sets: setsString });
          }
        }
      });
    } catch (e) {
      console.log(`Offline oder Fehler beim Laden der CSV für ${exercise}`, e);
    }
  }
};

export const saveSet = async (exercise: 'dips' | 'pullups', newSetsInput: string | number) => {
  const today = getTodayISO();
  const newSetsStr = String(newSetsInput).trim();

  const existing = await db.fitnessLogs.where({ date: today, exercise }).first();
  let updatedSetsString = newSetsStr;

  if (existing && existing.sets) {
    updatedSetsString = `${existing.sets},${newSetsStr}`;
    await db.fitnessLogs.update(existing.id!, { sets: updatedSetsString, synced: 0 });
  } else {
    await db.fitnessLogs.add({ date: today, exercise, sets: updatedSetsString, synced: 0 });
  }

  try {
    const res = await fetch('/api/fitness/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        exercise: exercise, 
        sets: newSetsStr 
      })
    });

    if (res.ok) {
      await db.fitnessLogs.where({ date: today, exercise }).modify({ synced: 1 });
      await syncFromCSV();
    } else {
      const errorText = await res.text();
      console.error("Server hat abgelehnt:", errorText);
    }
  } catch (e) {
    console.log("Server offline – Eintrag bleibt lokal in Dexie.");
  }
};