export const TRIP_ACTIVITY_TAGS = ['cycling', 'running', 'hiking', 'skiing', 'kayaking'] as const
export type TripActivityTag = (typeof TRIP_ACTIVITY_TAGS)[number]
