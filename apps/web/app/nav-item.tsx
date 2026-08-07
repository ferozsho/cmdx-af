'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export function NavItem({
  href,
  label,
  icon,
  badge,
}: {
  href: string
  label: string
  icon: string
  badge?: string
}) {
  const pathname = usePathname()
  const isActive = pathname === href ||
    (href !== '/' && pathname.startsWith(href))

  return (
    <Link
      href={href}
      className={`flex items-center gap-[10px] py-[11px] px-3 rounded-[10px] my-1 transition-colors ${
        isActive
          ? 'bg-[#202d4f] text-white'
          : 'text-[#b8c1d9] hover:bg-[#202d4f] hover:text-white'
      }`}
    >
      <span className="w-[22px] text-center">{icon}</span>
      <span className="text-[13px]">{label}</span>
      {badge && (
        <span className="ml-auto bg-[#3b4a6b] text-[#dfe6fa] rounded-[10px] px-[7px] py-[2px] text-[11px]">
          {badge}
        </span>
      )}
    </Link>
  )
}
