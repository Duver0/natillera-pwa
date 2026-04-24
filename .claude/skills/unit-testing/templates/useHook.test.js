// Plantilla para tests de hooks React con Vitest + Testing Library
// Copia este archivo a frontend/src/__tests__/use<Hook>.test.js

import { renderHook, act, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
// import { useFeature } from '../hooks/useFeature';

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      uid: 'test-uid',
      getIdToken: vi.fn().mockResolvedValue('fake-token'),
    },
    loading: false,
  }),
}));

vi.mock('../services/featureService', () => ({
  getFeature: vi.fn(),
}));

describe('useFeature', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── Happy Path ──────────────────────────────────────────────────────────

  it('returns data after successful fetch', async () => {
    // const { getFeature } = await import('../services/featureService');
    // vi.mocked(getFeature).mockResolvedValue({ name: 'Test' });
    //
    // const { result } = renderHook(() => useFeature());
    //
    // await waitFor(() => {
    //   expect(result.current.loading).toBe(false);
    // });
    //
    // expect(result.current.data).toEqual({ name: 'Test' });
    // expect(result.current.error).toBeNull();
  });

  // ─── Error Path ─────────────────────────────────────────────────────────

  it('sets error when fetch fails', async () => {
    // const { getFeature } = await import('../services/featureService');
    // vi.mocked(getFeature).mockRejectedValue(new Error('API Error'));
    //
    // const { result } = renderHook(() => useFeature());
    //
    // await waitFor(() => {
    //   expect(result.current.loading).toBe(false);
    // });
    //
    // expect(result.current.error).toBeInstanceOf(Error);
    // expect(result.current.data).toBeNull();
  });

  // ─── Edge Cases ─────────────────────────────────────────────────────────

  it('does not fetch when user is null', async () => {
    // vi.mocked from useAuth: user = null
    // const { result } = renderHook(() => useFeature());
    // await act(async () => {});
    // expect(result.current.loading).toBe(true); // never resolves without user
  });
});
