import { describe, it, expect } from 'vitest'
import { chunkArray } from '../chunk'

describe('chunkArray', () => {
  it('chunks array into correct sizes', () => {
    const arr = [1, 2, 3, 4, 5, 6, 7]
    const result = chunkArray(arr, 3)
    expect(result).toEqual([[1, 2, 3], [4, 5, 6], [7]])
  })

  it('handles exact division', () => {
    const arr = [1, 2, 3, 4, 5, 6]
    const result = chunkArray(arr, 3)
    expect(result).toEqual([[1, 2, 3], [4, 5, 6]])
  })

  it('handles empty array', () => {
    const result = chunkArray([], 3)
    expect(result).toEqual([])
  })

  it('handles chunk size larger than array', () => {
    const arr = [1, 2, 3]
    const result = chunkArray(arr, 10)
    expect(result).toEqual([[1, 2, 3]])
  })

  it('handles chunk size of 1', () => {
    const arr = [1, 2, 3]
    const result = chunkArray(arr, 1)
    expect(result).toEqual([[1], [2], [3]])
  })

  it('works with different types', () => {
    const arr = ['a', 'b', 'c', 'd']
    const result = chunkArray(arr, 2)
    expect(result).toEqual([['a', 'b'], ['c', 'd']])
  })

  it('preserves object references', () => {
    const obj1 = { id: 1 }
    const obj2 = { id: 2 }
    const arr = [obj1, obj2]
    const result = chunkArray(arr, 1)
    expect(result[0][0]).toBe(obj1)
    expect(result[1][0]).toBe(obj2)
  })
})
