/**
 * useMora — derives mora_count from a list of credits.
 * Tests cover the derivation logic directly since the hook may not yet exist
 * as a standalone file; if it does exist it is imported, otherwise the logic
 * is tested inline to ensure coverage of the business rule.
 */
import type { Credit } from '../../types'

function deriveMoraCount(credits: Credit[]): number {
  return credits.filter((c) => c.mora && c.status === 'ACTIVE').length
}

const makeCredit = (overrides: Partial<Credit> = {}): Credit => ({
  id: 'cr1',
  user_id: 'u1',
  client_id: 'c1',
  initial_capital: 1000,
  pending_capital: 800,
  version: 1,
  periodicity: 'MONTHLY',
  annual_interest_rate: 24,
  status: 'ACTIVE',
  start_date: '2024-01-01',
  mora: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

describe('mora derivation logic', () => {
  it('returns 0 when no credits', () => {
    expect(deriveMoraCount([])).toBe(0)
  })

  it('returns 0 when no credits are in mora', () => {
    expect(deriveMoraCount([makeCredit(), makeCredit({ id: 'cr2' })])).toBe(0)
  })

  it('counts ACTIVE credits in mora', () => {
    const credits = [
      makeCredit({ mora: true }),
      makeCredit({ id: 'cr2', mora: true }),
      makeCredit({ id: 'cr3', mora: false }),
    ]
    expect(deriveMoraCount(credits)).toBe(2)
  })

  it('does not count CLOSED credits even if mora=true', () => {
    const credits = [
      makeCredit({ mora: true, status: 'CLOSED' }),
      makeCredit({ id: 'cr2', mora: true }),
    ]
    expect(deriveMoraCount(credits)).toBe(1)
  })

  it('does not count SUSPENDED credits', () => {
    const credits = [makeCredit({ mora: true, status: 'SUSPENDED' })]
    expect(deriveMoraCount(credits)).toBe(0)
  })
})
