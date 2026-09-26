import { db } from './schema';
import type { Trip } from '@/data/trips';

export const syncTrips = async () => {
  try {
    // Dieser Fetch geht an deinen FastAPI Endpunkt, der die Trips-Liste liefert
    const res = await fetch('/api/trips/meta');
    if (!res.ok) throw new Error('Server nicht erreichbar');

    const data: Trip[] = await res.json();

    await db.transaction('rw', db.trips, async () => {
      for (const trip of data) {
        // Wir speichern das Datum extra für die Sortierung
        await db.trips.put(trip);
      }
    });
  } catch (e) {
    console.error("Trips konnten nicht gesynct werden, nutze Cache.");
  }
};