import { useState } from 'react'

export default function AccountForm({ onSignIn }) {
  const [registering, setRegistering] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      const response = await fetch(registering ? '/auth/register' : '/auth/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: data.get('email'), password: data.get('password') }),
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(typeof result.detail === 'string' ? result.detail : 'Check your email and password.')
      }
      onSignIn(result)
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel account-panel">
      <h1>{registering ? 'Create your PaperX account' : 'Sign in to PaperX'}</h1>
      <form className="create-form" onSubmit={submit}>
        <label htmlFor="account-email">Email</label>
        <input id="account-email" name="email" type="email" autoComplete="username" maxLength={254} required />
        <label htmlFor="account-password">Password</label>
        <input id="account-password" name="password" type="password"
          autoComplete={registering ? 'new-password' : 'current-password'}
          minLength={12} maxLength={128} required />
        {registering && <small>Use at least 12 characters.</small>}
        {error && <p role="alert">{error}</p>}
        <button disabled={busy} type="submit">{registering ? 'Create account' : 'Sign in'}</button>
        <button type="button" disabled={busy} onClick={() => {
          setError('')
          setRegistering((previous) => !previous)
        }}>
          {registering ? 'I already have an account' : 'Create an account'}
        </button>
      </form>
    </section>
  )
}
