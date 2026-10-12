// A small hash router: the URL after "#" is the app path, so a static host or
// the FastAPI SPA fallback can serve every route from index.html.
import { useSyncExternalStore } from 'react'

function subscribe(onChange: () => void) {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

function currentHash(): string {
  return window.location.hash.replace(/^#/, '') || '/'
}

export interface Location {
  path: string
  query: URLSearchParams
}

export function useLocation(): Location {
  const hash = useSyncExternalStore(subscribe, currentHash)
  const [path, search = ''] = hash.split('?')
  return { path: path || '/', query: new URLSearchParams(search) }
}

export function navigate(to: string) {
  window.location.hash = to
}

/** Match "/clients/:id/:tab?" style patterns; returns params or null. */
export function matchPath(pattern: string, path: string): Record<string, string> | null {
  const patternParts = pattern.split('/').filter(Boolean)
  const pathParts = path.split('/').filter(Boolean)
  const params: Record<string, string> = {}
  for (let i = 0; i < patternParts.length; i++) {
    const part = patternParts[i]
    const optional = part.endsWith('?')
    const value = pathParts[i]
    if (part.startsWith(':')) {
      if (value === undefined) {
        if (optional) continue
        return null
      }
      params[part.slice(1).replace(/\?$/, '')] = decodeURIComponent(value)
    } else if (part !== value) {
      return null
    }
  }
  return pathParts.length <= patternParts.length ? params : null
}
