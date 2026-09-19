import type { Stop } from './types'

/**
 * 10 stops have no `name` upstream and the extractor falls back to "node/<osm id>".
 * Showing that raw looks like a bug, so it gets a label and the id is surfaced
 * separately.
 */
const UNNAMED = /^node\/\d+$/

export function isUnnamed(name: string): boolean {
  return UNNAMED.test(name)
}

export function stopLabel(stop: Pick<Stop, 'name'>): string {
  return isUnnamed(stop.name) ? 'Unnamed stop' : stop.name
}

/**
 * Route refs are NOT all numeric: "А", "1а", "39а", "т1" sit alongside "1" and "16".
 * parseInt would collapse "1а" onto "1", so purely-numeric refs sort numerically and
 * everything else sorts as a string after them. This mirrors `route_sort_key` in
 * app/backend/tramgraph.py, so the UI lists refs in the same order as the API.
 */
export function compareRouteRefs(a: string, b: string): number {
  const aNum = /^\d+$/.test(a)
  const bNum = /^\d+$/.test(b)
  if (aNum && bNum) return Number(a) - Number(b)
  if (aNum) return -1
  if (bNum) return 1
  return a.localeCompare(b, 'ru')
}

export function sortRouteRefs(refs: readonly string[]): string[] {
  return [...refs].sort(compareRouteRefs)
}

export function formatKm(metres: number): string {
  if (metres < 1000) return `${Math.round(metres)} m`
  return `${(metres / 1000).toFixed(metres < 10000 ? 2 : 1)} km`
}

export function formatNumber(value: number): string {
  return value.toLocaleString('en-US')
}

/** "2026-09-18T20:20:11Z" -> "18 Sep 2026, 20:20 UTC". Never throws on junk input. */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return 'unknown'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const formatted = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  }).format(date)
  return `${formatted} UTC`
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${formatNumber(count)} ${count === 1 ? one : many}`
}
