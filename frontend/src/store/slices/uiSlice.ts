import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface UiState {
  selectedClientId: string | null
  selectedCreditId: string | null
  activeModal: string | null
  notification: { type: 'success' | 'error' | 'info'; message: string } | null
}

const initialState: UiState = {
  selectedClientId: null,
  selectedCreditId: null,
  activeModal: null,
  notification: null,
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    selectClient(state, action: PayloadAction<string | null>) {
      state.selectedClientId = action.payload
    },
    selectCredit(state, action: PayloadAction<string | null>) {
      state.selectedCreditId = action.payload
    },
    openModal(state, action: PayloadAction<string>) {
      state.activeModal = action.payload
    },
    closeModal(state) {
      state.activeModal = null
    },
    showNotification(state, action: PayloadAction<UiState['notification']>) {
      state.notification = action.payload
    },
    clearNotification(state) {
      state.notification = null
    },
  },
})

export const {
  selectClient,
  selectCredit,
  openModal,
  closeModal,
  showNotification,
  clearNotification,
} = uiSlice.actions
export default uiSlice.reducer
