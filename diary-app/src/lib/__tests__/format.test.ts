import { describe, it, expect } from 'vitest'
import { formatDateTimeEU } from '../format'
import { formatDateEU } from '../date'

describe('formatDateTimeEU', () => {
  it('formats ISO datetime string correctly', () => {
    // Use a local timezone time to avoid timezone conversion issues
    const result = formatDateTimeEU('2024-01-15T10:30:00')
    expect(result).toBe('15.01.2024 10:30')
  })

  it('converts UTC to local timezone', () => {
    // Test that UTC times are converted to local time
    const utcTime = '2024-01-15T10:30:00+00:00'
    const result = formatDateTimeEU(utcTime)
    const date = new Date(utcTime)
    const expectedHours = String(date.getHours()).padStart(2, '0')
    const expectedMinutes = String(date.getMinutes()).padStart(2, '0')
    expect(result).toBe(`15.01.2024 ${expectedHours}:${expectedMinutes}`)
  })

  it('handles null input', () => {
    expect(formatDateTimeEU(null)).toBe('')
  })

  it('handles undefined input', () => {
    expect(formatDateTimeEU(undefined)).toBe('')
  })

  it('handles empty string', () => {
    expect(formatDateTimeEU('')).toBe('')
  })

  it('handles invalid date', () => {
    const result = formatDateTimeEU('invalid-date')
    expect(result).toBe('invalid-date')
  })

  it('pads single digit day and month', () => {
    // Use local timezone time
    const result = formatDateTimeEU('2024-01-05T09:05:00')
    expect(result).toBe('05.01.2024 09:05')
  })

  it('handles different timezones', () => {
    const result = formatDateTimeEU('2024-01-15T10:30:00+05:00')
    // Should still format correctly (timezone conversion handled by Date)
    expect(result).toContain('15.01.2024')
    // Verify it's a valid format: DD.MM.YYYY HH:MM
    expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/)
  })

  it('formats date and time components correctly', () => {
    const result = formatDateTimeEU('2024-12-31T23:59:00')
    expect(result).toBe('31.12.2024 23:59')
  })
})

describe('formatDateEU', () => {
  it('formats ISO date string correctly', () => {
    expect(formatDateEU('2024-01-15')).toBe('15.01.2024')
  })

  it('pads single digit day and month', () => {
    expect(formatDateEU('2024-01-05')).toBe('05.01.2024')
  })

  it('handles invalid format', () => {
    expect(formatDateEU('invalid')).toBe('invalid')
    expect(formatDateEU('2024/01/15')).toBe('2024/01/15')
  })

  it('handles edge cases', () => {
    expect(formatDateEU('2024-12-31')).toBe('31.12.2024')
    expect(formatDateEU('2024-01-01')).toBe('01.01.2024')
  })
})
