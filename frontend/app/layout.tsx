import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import NoReloadGuard from '@/components/NoReloadGuard'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Zero Trust Architecture System',
  description: 'AI-based behavior tracking and dynamic trust scoring system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <NoReloadGuard />
          {children}
        </div>
      </body>
    </html>
  )
}
