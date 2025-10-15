import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import GuestAuthProvider from '../components/GuestAuthProvider'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'MC Press Chatbot - AI-Powered Document Assistant',
  description: 'Ask questions about MC Press technical books and documentation',
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