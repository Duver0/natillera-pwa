import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../hooks/useAuth'
import { PasswordInput } from '../components/PasswordInput'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z
    .string()
    .min(8, 'At least 8 characters')
    .regex(/[A-Z]/, 'Must contain an uppercase letter')
    .regex(/[0-9]/, 'Must contain a number'),
  password_confirm: z.string(),
}).refine((d) => d.password === d.password_confirm, {
  message: 'Passwords do not match',
  path: ['password_confirm'],
})

type FormData = z.infer<typeof schema>

function passwordStrength(password: string): { score: number; label: string; color: string } {
  if (!password) return { score: 0, label: '', color: 'bg-gray-200' }
  let score = 0
  if (password.length >= 8) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password)) score++
  const levels = [
    { label: 'Weak', color: 'bg-red-500' },
    { label: 'Fair', color: 'bg-yellow-500' },
    { label: 'Good', color: 'bg-blue-500' },
    { label: 'Strong', color: 'bg-green-500' },
  ]
  const level = levels[Math.min(score - 1, 3)] ?? { label: 'Weak', color: 'bg-red-500' }
  return { score, label: level.label, color: level.color }
}

export function RegisterPage() {
  const { register: registerAuth, registerLoading } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [passwordValue, setPasswordValue] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const strength = passwordStrength(passwordValue)

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await registerAuth(data.email, data.password)
    } catch (e: any) {
      setError(e?.data?.detail ?? 'Registration failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Create account</h1>

        {error && (
          <div role="alert" aria-live="assertive" className="mb-4 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="mb-4">
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              id="email"
              type="email"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              {...register('email')}
            />
            {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
          </div>

          <div className="mb-4">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              {...register('password', { onChange: (e) => setPasswordValue(e.target.value) })}
            />
            {passwordValue && (
              <div className="mt-2" aria-label={`Password strength: ${strength.label}`}>
                <div className="flex gap-1 h-1.5">
                  {[1, 2, 3, 4].map((n) => (
                    <div
                      key={n}
                      className={`flex-1 rounded-full ${n <= strength.score ? strength.color : 'bg-gray-200'}`}
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">{strength.label}</p>
              </div>
            )}
            {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
          </div>

          <div className="mb-6">
            <label htmlFor="password_confirm" className="block text-sm font-medium text-gray-700 mb-1">Confirm password</label>
            <PasswordInput
              id="password_confirm"
              autoComplete="new-password"
              {...register('password_confirm')}
            />
            {errors.password_confirm && <p className="text-xs text-red-500 mt-1">{errors.password_confirm.message}</p>}
          </div>

          <button
            type="submit"
            disabled={registerLoading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {registerLoading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <p className="mt-4 text-sm text-center text-gray-600">
          Have an account? <Link to="/login" className="text-blue-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
