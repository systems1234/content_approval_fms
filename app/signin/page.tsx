'use client'

import { signIn } from 'next-auth/react'

export default function SignInPage() {
  return (
    <div className="center-page">
      <div className="center-box">
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <b style={{ fontSize: 22, fontWeight: 700 }}>content</b>
          <span style={{ fontSize: 13, color: 'var(--muted)', marginLeft: 4 }}>fms</span>
        </div>
        <div className="center-panel">
          <h1>Sign in</h1>
          <p>Use your @gempundit.com Google account. You need to be added to the Users table first.</p>
          <button
            className="btn wide"
            onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
          >
            <span style={{
              width: 20, height: 20, borderRadius: '50%',
              background: 'var(--accent)', color: '#fff',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 700, marginRight: 4,
            }}>G</span>
            Continue with Google
          </button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--faint)', marginTop: 22, textAlign: 'center', lineHeight: 1.5 }}>
          Restricted to gempundit.com.<br />
          Not working? Ask an admin to check your access in the People page.
        </p>
      </div>
    </div>
  )
}
