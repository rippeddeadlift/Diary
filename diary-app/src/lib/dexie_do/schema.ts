import Dexie, { type Table } from 'dexie';
import type { FitnessEntry } from './fitness';
import type { Trip } from '@/data/trips';

export class DiaryDB extends Dexie {
  fitnessLogs!: Table<FitnessEntry>;
  trips!: Table<Trip>;

  constructor() {
    super('DiaryDB');
    this.version(2).stores({
      // Version erhöht auf 2 wegen der neuen trips Tabelle
      fitnessLogs: '++id, date, exercise, synced, [date+exercise]',
      trips: 'id, meta.date, meta.title' // id ist hier der String aus deiner Trip-Struktur
    });
  }
}

export const db = new DiaryDB();