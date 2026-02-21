export const PEOPLE = [
  'ivan',
  'nastya',
  'alexey',
  'tatiana',
  'leo',
  'bartek',
  'michal',
  'mksaf',
  'loewa'
] as const
export type Person = (typeof PEOPLE)[number]

export const PHOTO_TAGS = ['family', 'friends', 'food', 'nature', 'cycling', 'art', 'travel', 'sights'] as const
export type PhotoTag = (typeof PHOTO_TAGS)[number]

export const TRIP_ACTIVITY_TAGS = ['cycling', 'running', 'hiking', 'skiing', 'kayaking', 'skating'] as const
export type TripActivityTag = (typeof TRIP_ACTIVITY_TAGS)[number]
