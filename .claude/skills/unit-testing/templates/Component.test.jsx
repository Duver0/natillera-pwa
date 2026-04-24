// Plantilla para tests de componentes React con Vitest + Testing Library
// Copia este archivo a frontend/src/__tests__/<Component>.test.jsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
// import FeatureComponent from '../components/FeatureComponent';

// Mock de módulos externos
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { uid: 'test-uid', getIdToken: vi.fn().mockResolvedValue('fake-token') }, loading: false }),
}));

vi.mock('../services/featureService', () => ({
  getFeature: vi.fn().mockResolvedValue({ name: 'Test Feature' }),
}));

describe('FeatureComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── Happy Path ──────────────────────────────────────────────────────────

  it('renders the component title', () => {
    // render(<FeatureComponent title="My Feature" />);
    // expect(screen.getByRole('heading', { name: /my feature/i })).toBeInTheDocument();
  });

  it('displays data after loading', async () => {
    // render(<FeatureComponent />);
    // await waitFor(() => {
    //   expect(screen.getByText('Test Feature')).toBeInTheDocument();
    // });
  });

  // ─── Error Path ─────────────────────────────────────────────────────────

  it('shows error message when fetch fails', async () => {
    // vi.mocked(getFeature).mockRejectedValueOnce(new Error('Network error'));
    // render(<FeatureComponent />);
    // await waitFor(() => {
    //   expect(screen.getByText(/error/i)).toBeInTheDocument();
    // });
  });

  // ─── User Interactions ───────────────────────────────────────────────────

  it('calls onSubmit with input value when form is submitted', async () => {
    // const onSubmit = vi.fn();
    // render(<FeatureComponent onSubmit={onSubmit} />);
    // await userEvent.type(screen.getByRole('textbox', { name: /name/i }), 'hello');
    // await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    // expect(onSubmit).toHaveBeenCalledWith('hello');
  });
});
