"use client"

import { useEffect } from 'react'

// Client-side guard to prevent scripts from programmatically reloading the page.
// This makes window.location.reload and history-based reload attempts no-ops so
// accidental hard reloads (for example from HMR/dev-client or other scripts)
// won't interrupt a long-running training session.
export default function NoReloadGuard() {
  useEffect(() => {
    try {
      // Override programmatic reload
      // @ts-ignore - assigning to location.reload is allowed in browser
      window.location.reload = () => {
        console.info('Suppressed programmatic window.location.reload()')
      }

      // Prevent router code from calling location.assign for reloads
      // @ts-ignore
      const originalAssign = window.location.assign
      // @ts-ignore
      window.location.assign = (url?: string) => {
        console.info('Suppressed programmatic window.location.assign ->', url)
      }

      // Optional: prevent replace which may also trigger navigation
      // @ts-ignore
      window.location.replace = (url?: string) => {
        console.info('Suppressed programmatic window.location.replace ->', url)
      }

      // If any code tries to call history.back/forward that triggers reloads,
      // we don't override those to keep native navigation working.
    } catch (e) {
      console.warn('NoReloadGuard: failed to install guards', e)
    }
  }, [])

  return null
}
