import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import GuestAuthProvider from '../components/GuestAuthProvider'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'MC ChatMaster | Instant AI-Powered IBM i Expertise',
  description: 'Your 24/7 AI-powered guide to mastering RPG, DB2, System Administration, and IBM i best practices from MC Press technical books and articles',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        <GuestAuthProvider>
          <div className="min-h-screen bg-gray-50">
            {children}
          </div>
        </GuestAuthProvider>
      </body>
    </html>
  )
}