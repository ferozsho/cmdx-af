import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="max-w-md mx-auto text-center py-16 space-y-4 font-mono">
      <h2 className="text-2xl font-bold text-white">404 - Page Not Found</h2>
      <p className="text-xs text-gray-400">The requested workspace route or page does not exist.</p>
      <Link
        href="/"
        className="inline-block bg-blue-600 text-white px-4 py-2 rounded text-xs font-sans font-semibold hover:bg-blue-500 transition-colors"
      >
        Return to Dashboard
      </Link>
    </div>
  )
}
