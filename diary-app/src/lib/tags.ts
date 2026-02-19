import { PEOPLE, PHOTO_TAGS, TRIP_ACTIVITY_TAGS } from '@/data/tagConfig'
import type { Person, PhotoTag, TripActivityTag } from '@/data/tagConfig'
import type { GalleryItem } from '@/types/photos'

export function normalizePeople(people: string[] | undefined): Person[] {
  return (people ?? []).filter((p): p is Person => PEOPLE.includes(p as Person))
}

export function normalizeTags(tags: string[] | undefined): PhotoTag[] {
  return (tags ?? []).filter((t): t is PhotoTag => PHOTO_TAGS.includes(t as PhotoTag))
}

export function normalizeTripTags(tags: string[] | undefined): TripActivityTag[] {
  return (tags ?? []).filter((t): t is TripActivityTag => TRIP_ACTIVITY_TAGS.includes(t as TripActivityTag))
}

// For GalleryItem from loose API
export function normalizeGalleryItem(raw: any): GalleryItem {
  return {
    path: raw.path,
    url: raw.url,
    hasSidecar: raw.hasSidecar,
    thumbUrl: raw.thumbUrl ?? null,
    thumbExists: raw.thumbExists ?? false,
    people: normalizePeople(raw.people),
    tags: normalizeTags(raw.tags),
    createdAt: raw.createdAt ?? null,
    location: raw.location ?? null,
    missing: raw.missing ?? false
  }
}
