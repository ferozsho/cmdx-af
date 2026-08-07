import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="max-w-md mx-auto text-center py-16 space-y-4 font-mono">
      <h2 className="text-2xl font-bold text-foreground font-sans">404 - Page Not Found</h2>
      <p className="text-xs text-muted font-sans">The requested workspace route or page does not exist.</p>
      <Link
        href="/"
        className="inline-block btn-primary-af text-xs font-sans"
      >
        Return to Dashboard
      </Link>
    </div>
  )
}
