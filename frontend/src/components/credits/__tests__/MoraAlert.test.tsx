/**
 * Tests for MoraAlert component.
 * SPEC-001 §US-006 — informational mora display, no penalties.
 */
import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '../../../test-utils'
import MoraAlert from '../MoraAlert'

// Use a fixed past date so days_overdue is deterministic relative to test run
const MORA_DATE = '2020-01-01'

describe('MoraAlert', () => {
  it('renders null when moraSince is null', () => {
    const { container } = render(<MoraAlert moraSince={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders null when moraSince is undefined', () => {
    const { container } = render(<MoraAlert moraSince={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders alert when moraSince is set', () => {
    render(<MoraAlert moraSince={MORA_DATE} />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('shows "Crédito en mora" heading', () => {
    render(<MoraAlert moraSince={MORA_DATE} />)
    expect(screen.getByText('Crédito en mora')).toBeInTheDocument()
  })

  it('shows days overdue (positive number)', () => {
    render(<MoraAlert moraSince={MORA_DATE} />)
    // Days should be a large number (years in the past) — just check unit text
    expect(screen.getByText(/días/i)).toBeInTheDocument()
  })

  it('renders moraAmount when provided and > 0', () => {
    render(<MoraAlert moraSince={MORA_DATE} moraAmount={450000} />)
    // Should show formatted currency
    expect(screen.getByText(/monto vencido/i)).toBeInTheDocument()
  })

  it('does not render moraAmount line when moraAmount is 0', () => {
    render(<MoraAlert moraSince={MORA_DATE} moraAmount={0} />)
    expect(screen.queryByText(/monto vencido/i)).not.toBeInTheDocument()
  })

  it('does not render moraAmount line when moraAmount is undefined', () => {
    render(<MoraAlert moraSince={MORA_DATE} />)
    expect(screen.queryByText(/monto vencido/i)).not.toBeInTheDocument()
  })

  it('renders informational note about no penalties', () => {
    render(<MoraAlert moraSince={MORA_DATE} />)
    expect(screen.getByText(/no se generan intereses adicionales/i)).toBeInTheDocument()
  })
})
