import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ClientForm } from '../ClientForm'

function setup(props = {}) {
  const onSubmit = vi.fn()
  const onCancel = vi.fn()
  render(<ClientForm onSubmit={onSubmit} onCancel={onCancel} {...props} />)
  return { onSubmit, onCancel }
}

describe('ClientForm', () => {
  it('renders all required fields', () => {
    setup()
    expect(screen.getByTestId('input-first-name')).toBeInTheDocument()
    expect(screen.getByTestId('input-last-name')).toBeInTheDocument()
    expect(screen.getByTestId('input-phone')).toBeInTheDocument()
    expect(screen.getByTestId('submit-client')).toBeInTheDocument()
  })

  it('shows validation errors when submitting empty form', async () => {
    setup()
    fireEvent.click(screen.getByTestId('submit-client'))
    await waitFor(() => {
      expect(screen.getByText('First name is required')).toBeInTheDocument()
      expect(screen.getByText('Last name is required')).toBeInTheDocument()
      expect(screen.getByText('Phone is required')).toBeInTheDocument()
    })
  })

  it('calls onSubmit with form data when valid', async () => {
    const { onSubmit } = setup()
    fireEvent.change(screen.getByTestId('input-first-name'), { target: { value: 'Ana' } })
    fireEvent.change(screen.getByTestId('input-last-name'), { target: { value: 'Lopez' } })
    fireEvent.change(screen.getByTestId('input-phone'), { target: { value: '3001234567' } })
    fireEvent.click(screen.getByTestId('submit-client'))
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ first_name: 'Ana', last_name: 'Lopez', phone: '3001234567' }),
        expect.anything()
      )
    })
  })

  it('calls onCancel when Cancel button is clicked', () => {
    const { onCancel } = setup()
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('disables submit and shows Saving... when isLoading=true', () => {
    setup({ isLoading: true })
    const btn = screen.getByTestId('submit-client')
    expect(btn).toBeDisabled()
    expect(btn).toHaveTextContent('Saving...')
  })

  it('pre-fills fields from initial prop', async () => {
    setup({
      initial: {
        first_name: 'Carlos',
        last_name: 'Perez',
        phone: '3109876543',
        document_id: 'CC123',
      },
    })
    await waitFor(() => {
      expect(screen.getByTestId('input-first-name')).toHaveValue('Carlos')
      expect(screen.getByTestId('input-last-name')).toHaveValue('Perez')
      expect(screen.getByTestId('input-phone')).toHaveValue('3109876543')
      expect(screen.getByTestId('input-document-id')).toHaveValue('CC123')
    })
  })

  it('uses custom submitLabel', () => {
    setup({ submitLabel: 'Create Client' })
    expect(screen.getByTestId('submit-client')).toHaveTextContent('Create Client')
  })

  it('does not render Cancel when onCancel is not provided', () => {
    render(<ClientForm onSubmit={vi.fn()} />)
    expect(screen.queryByText('Cancel')).not.toBeInTheDocument()
  })
})
