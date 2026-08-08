'use client'

import { useRouter } from 'next/navigation'
import { logout } from '@/lib/api'

/** Sign-out button — clears the stored JWT and returns to /login. */
export default function LogoutButton() {
  const router = useRouter()

  const handleLogout = () => {
    logout()
    router.replace('/login')
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      className="btn-secondary-af !px-[11px] !py-[9px] text-sm"
      aria-label="Sign out"
      title="Sign out"
    >
      ⏻
    </button>
  )
}
