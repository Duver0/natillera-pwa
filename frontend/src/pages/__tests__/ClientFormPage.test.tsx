/**
 * ClientFormPage — page integration test.
 * The project surfaces the form inside ClientListPage modal and via
 * the standalone ClientForm component. This test renders ClientForm
 * as a page-level integration with an initial values prop.
 */
import { render, screen } from '@testing-library/react'
import { ClientForm } from '../../components/ClientForm'

const INITIAL = {
  first_name: 'Maria',
  last_name: 'Torres',
  phone: '3205556666',
  document_id: 'CC999',
  address: 'Calle 10',
  notes: 'VIP client',
}

describe('ClientFormPage — renders form with initial values', () => {
  it('pre-populates all fields', async () => {
    render(<ClientForm onSubmit={vi.fn()} initial={INITIAL} />)
    // React Hook Form reset is async
    await screen.findByDisplayValue('Maria')
    expect(screen.getByDisplayValue('Torres')).toBeInTheDocument()
    expect(screen.getByDisplayValue('3205556666')).toBeInTheDocument()
    expect(screen.getByDisplayValue('CC999')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Calle 10')).toBeInTheDocument()
    expect(screen.getByDisplayValue('VIP client')).toBeInTheDocument()
  })

  it('shows Save button by default', async () => {
    render(<ClientForm onSubmit={vi.fn()} />)
    expect(screen.getByTestId('submit-client')).toHaveTextContent('Save')
  })

  it('shows custom submitLabel', async () => {
    render(<ClientForm onSubmit={vi.fn()} submitLabel="Update Client" />)
    expect(screen.getByTestId('submit-client')).toHaveTextContent('Update Client')
  })
})
