/**
 * Tests para la construccion de BASE_URL en apiSlice.
 *
 * Verifica los tres escenarios criticos:
 * 1. VITE_API_URL con HTTP -> debe convertirse a HTTPS
 * 2. VITE_API_URL con HTTPS -> debe usarse sin cambios
 * 3. VITE_API_URL undefined -> debe usar el fallback HTTPS hardcodeado
 *
 * Ademas verifica que ningun caso produzca triple-slash (https:///).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Funcion extraida de la logica de apiSlice para tests unitarios puros.
// Si se refactoriza apiSlice, actualizar tambien esta funcion.
function buildBaseUrl(envValue: string | undefined): string {
  const raw = envValue || 'https://natillera-pwa-production.up.railway.app'
  return raw.startsWith('http://') ? raw.replace('http://', 'https://') : raw
}

describe('buildBaseUrl — construccion segura de BASE_URL', () => {
  it('convierte http:// a https:// cuando VITE_API_URL es HTTP', () => {
    const result = buildBaseUrl('http://natillera-pwa-production.up.railway.app')
    expect(result).toBe('https://natillera-pwa-production.up.railway.app')
  })

  it('respeta https:// sin modificaciones cuando VITE_API_URL es HTTPS', () => {
    const result = buildBaseUrl('https://natillera-pwa-production.up.railway.app')
    expect(result).toBe('https://natillera-pwa-production.up.railway.app')
  })

  it('usa el fallback HTTPS cuando VITE_API_URL no esta definida (undefined)', () => {
    const result = buildBaseUrl(undefined)
    expect(result).toBe('https://natillera-pwa-production.up.railway.app')
  })

  it('usa el fallback HTTPS cuando VITE_API_URL es string vacio', () => {
    const result = buildBaseUrl('')
    expect(result).toBe('https://natillera-pwa-production.up.railway.app')
  })

  it('nunca produce triple-slash (https:///) con http:// como entrada', () => {
    const result = buildBaseUrl('http://natillera-pwa-production.up.railway.app')
    expect(result).not.toContain('https:///')
    expect(result).not.toContain('http://')
  })

  it('nunca produce triple-slash (https:///) con https:// como entrada', () => {
    const result = buildBaseUrl('https://natillera-pwa-production.up.railway.app')
    expect(result).not.toContain('https:///')
  })

  it('maneja URLs con path (con trailing slash) correctamente', () => {
    const result = buildBaseUrl('http://natillera-pwa-production.up.railway.app/')
    expect(result).toBe('https://natillera-pwa-production.up.railway.app/')
    expect(result).not.toContain('http://')
    expect(result).not.toContain('https:///')
  })

  it('siempre produce una URL que comienza con https://', () => {
    const cases = [
      'http://natillera-pwa-production.up.railway.app',
      'https://natillera-pwa-production.up.railway.app',
      undefined,
      '',
    ]
    for (const input of cases) {
      const result = buildBaseUrl(input)
      expect(result).toMatch(/^https:\/\//)
    }
  })
})
