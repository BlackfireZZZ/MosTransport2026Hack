import { useEffect, useRef, useState } from 'react'
// maplibre-gl v6 has named exports only; the v5 default export is gone.
// `Map` is aliased to MapLibreMap so it does not shadow the global Map.
import {
  AttributionControl,
  MapLibreMap,
  NavigationControl,
  Popup,
  ScaleControl,
} from 'maplibre-gl'
import { setWorkerUrl } from 'maplibre-gl'
import type { GeoJSONSource, LngLatBoundsLike, MapMouseEvent, PointLike } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FeatureCollection, Point } from 'geojson'
import type { GraphGeoJSON, PathResult, Stop } from '../types'
import { stopLabel } from '../format'

/**
 * A free, keyless vector basemap. CARTO serves this style and its tiles without an
 * API key or token, which keeps the whole app runnable from a clean checkout.
 */
const BASEMAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

/**
 * maplibre cannot find its own worker once the library has been bundled, and fails
 * silently when it cannot -- a blank canvas with working controls. The
 * maplibre-worker-assets plugin in vite.config.ts publishes the worker at this fixed
 * path in both dev and build; this points the library at it. BASE_URL keeps it correct
 * if the app is ever served from a sub-path.
 */
setWorkerUrl(`${import.meta.env.BASE_URL}maplibre/maplibre-gl-worker.mjs`)

/** Moscow, roughly framed on the tram network, used until the graph arrives. */
const INITIAL_CENTER: [number, number] = [37.62, 55.75]
const INITIAL_ZOOM = 10

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

const COLOR = {
  track: '#8d99a6',
  trackDim: '#c3cad2',
  route: '#c8102e',
  path: '#0a7d3f',
  stop: '#ffffff',
  stopStroke: '#6b7580',
  from: '#0a7d3f',
  to: '#c8102e',
  selected: '#1b64c8',
}

export interface MapCanvasProps {
  network: GraphGeoJSON | null
  routeGeo: GraphGeoJSON | null
  selectedRoute: string | null
  path: PathResult | null
  fromStop: Stop | null
  toStop: Stop | null
  selectedStop: Stop | null
  onStopClick: (id: number) => void
}

type Bounds = [number, number, number, number]

/** Bounding box over every coordinate in a FeatureCollection, or null if empty. */
function boundsOf(collection: GraphGeoJSON | null): Bounds | null {
  if (!collection?.features.length) return null
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  const visit = ([x, y]: number[]) => {
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
  }
  for (const feature of collection.features) {
    if (feature.geometry.type === 'Point') visit(feature.geometry.coordinates)
    else feature.geometry.coordinates.forEach(visit)
  }
  return Number.isFinite(minX) ? [minX, minY, maxX, maxY] : null
}

function boundsOfCoords(coords: [number, number][]): Bounds | null {
  if (!coords.length) return null
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const [x, y] of coords) {
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
  }
  return [minX, minY, maxX, maxY]
}

/** Points for the from / to / selected pins, drawn on top of everything else. */
function markerCollection(
  fromStop: Stop | null,
  toStop: Stop | null,
  selectedStop: Stop | null,
): FeatureCollection<Point, { role: string; label: string }> {
  const seen = new Set<number>()
  const features: FeatureCollection<Point, { role: string; label: string }>['features'] = []
  const push = (stop: Stop | null, role: string) => {
    // from/to/selected often point at the same stop; the first role wins so the
    // endpoint colours are not overpainted by the generic selection ring.
    if (!stop || seen.has(stop.id)) return
    seen.add(stop.id)
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [stop.lon, stop.lat] },
      properties: { role, label: stopLabel(stop) },
    })
  }
  push(fromStop, 'from')
  push(toStop, 'to')
  push(selectedStop, 'selected')
  return { type: 'FeatureCollection', features }
}

export function MapCanvas(props: MapCanvasProps) {
  const { network, routeGeo, selectedRoute, path, fromStop, toStop, selectedStop, onStopClick } =
    props

  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const popupRef = useRef<Popup | null>(null)
  const [ready, setReady] = useState(false)
  const [styleError, setStyleError] = useState<string | null>(null)
  // The first network payload frames the map; later ones (route filters) must not
  // yank the viewport back out again.
  const framedRef = useRef(false)

  // The click handler lives in a ref so the map is built exactly once rather than torn
  // down whenever the parent hands down a new callback identity. Assigned in an effect,
  // not during render, because a ref must not be mutated while rendering.
  const onStopClickRef = useRef(onStopClick)
  useEffect(() => {
    onStopClickRef.current = onStopClick
  }, [onStopClick])

  useEffect(() => {
    if (!containerRef.current) return undefined

    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      attributionControl: false,
    })
    mapRef.current = map

    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ maxWidth: 120, unit: 'metric' }), 'bottom-left')
    map.addControl(
      new AttributionControl({
        compact: true,
        // Legally required for an OSM-derived dataset, and the basemap wants credit too.
        customAttribution:
          '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">&copy; OpenStreetMap contributors, ODbL 1.0</a>',
      }),
      'bottom-right',
    )

    map.on('error', (event) => {
      // A dead basemap CDN should say so rather than leaving a blank grey rectangle.
      const message = event.error?.message ?? 'unknown map error'
      if (/style|sprite|glyphs|tiles/i.test(message)) setStyleError(message)
      console.error('[maplibre]', message)
    })

    map.on('load', () => {
      map.addSource('network', { type: 'geojson', data: EMPTY })
      map.addSource('route', { type: 'geojson', data: EMPTY })
      map.addSource('path', { type: 'geojson', data: EMPTY })
      map.addSource('markers', { type: 'geojson', data: EMPTY })

      map.addLayer({
        id: 'network-track',
        type: 'line',
        source: 'network',
        filter: ['==', ['geometry-type'], 'LineString'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': COLOR.track, 'line-width': 1.6, 'line-opacity': 0.85 },
      })

      map.addLayer({
        id: 'network-stops',
        type: 'circle',
        source: 'network',
        filter: ['==', ['geometry-type'], 'Point'],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 1.8, 12, 3.2, 16, 6],
          'circle-color': COLOR.stop,
          'circle-stroke-color': COLOR.stopStroke,
          'circle-stroke-width': 1.2,
        },
      })

      map.addLayer({
        id: 'route-track',
        type: 'line',
        source: 'route',
        filter: ['==', ['geometry-type'], 'LineString'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': COLOR.route, 'line-width': 3.4 },
      })

      map.addLayer({
        id: 'path-track',
        type: 'line',
        source: 'path',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': COLOR.path, 'line-width': 5, 'line-opacity': 0.9 },
      })

      map.addLayer({
        id: 'route-stops',
        type: 'circle',
        source: 'route',
        filter: ['==', ['geometry-type'], 'Point'],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 2.6, 12, 4.2, 16, 7],
          'circle-color': COLOR.stop,
          'circle-stroke-color': COLOR.route,
          'circle-stroke-width': 2,
        },
      })

      map.addLayer({
        id: 'marker-points',
        type: 'circle',
        source: 'markers',
        paint: {
          'circle-radius': 8,
          'circle-color': [
            'match',
            ['get', 'role'],
            'from',
            COLOR.from,
            'to',
            COLOR.to,
            COLOR.selected,
          ],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2.5,
        },
      })

      setReady(true)
    })

    const clickLayers = ['marker-points', 'route-stops', 'network-stops']

    const handleClick = (event: MapMouseEvent) => {
      // A few pixels of slop: the stop dots are small and Moscow has a lot of them.
      const box: [PointLike, PointLike] = [
        [event.point.x - 6, event.point.y - 6],
        [event.point.x + 6, event.point.y + 6],
      ]
      const layers = clickLayers.filter((id) => map.getLayer(id))
      if (!layers.length) return
      const hits = map.queryRenderedFeatures(box, { layers })
      const hit = hits.find((feature) => feature.properties?.id !== undefined)
      if (!hit) return
      const id = Number(hit.properties.id)
      if (Number.isFinite(id)) onStopClickRef.current(id)
    }
    map.on('click', handleClick)

    const hoverLayers = ['route-stops', 'network-stops']
    const popup = new Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 10,
      className: 'stop-tip',
    })
    popupRef.current = popup

    const handleMove = (event: MapMouseEvent) => {
      const layers = hoverLayers.filter((id) => map.getLayer(id))
      if (!layers.length) return
      const box: [PointLike, PointLike] = [
        [event.point.x - 5, event.point.y - 5],
        [event.point.x + 5, event.point.y + 5],
      ]
      const hit = map.queryRenderedFeatures(box, { layers })[0]
      map.getCanvas().style.cursor = hit ? 'pointer' : ''
      if (!hit || hit.geometry.type !== 'Point') {
        popup.remove()
        return
      }
      const name = String(hit.properties.name ?? '')
      popup
        .setLngLat(hit.geometry.coordinates as [number, number])
        .setText(stopLabel({ name }))
        .addTo(map)
    }
    map.on('mousemove', handleMove)

    return () => {
      popup.remove()
      map.remove()
      mapRef.current = null
      setReady(false)
    }
  }, [])

  // --- data -> sources -------------------------------------------------------

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const source = map.getSource('network') as GeoJSONSource | undefined
    source?.setData((network ?? EMPTY) as FeatureCollection)

    if (network && !framedRef.current) {
      const bounds = boundsOf(network)
      if (bounds) {
        map.fitBounds(bounds as LngLatBoundsLike, { padding: 48, duration: 0 })
        framedRef.current = true
      }
    }
  }, [network, ready])

  // Dim the whole network while one route is isolated, so the route reads clearly.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready || !map.getLayer('network-track')) return
    const dimmed = Boolean(selectedRoute)
    map.setPaintProperty('network-track', 'line-color', dimmed ? COLOR.trackDim : COLOR.track)
    map.setPaintProperty('network-track', 'line-opacity', dimmed ? 0.55 : 0.85)
    map.setPaintProperty('network-stops', 'circle-opacity', dimmed ? 0.35 : 1)
    map.setPaintProperty('network-stops', 'circle-stroke-opacity', dimmed ? 0.35 : 1)
  }, [selectedRoute, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const source = map.getSource('route') as GeoJSONSource | undefined
    source?.setData((routeGeo ?? EMPTY) as FeatureCollection)

    const bounds = boundsOf(routeGeo)
    if (bounds) map.fitBounds(bounds as LngLatBoundsLike, { padding: 64, duration: 600 })
  }, [routeGeo, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const source = map.getSource('path') as GeoJSONSource | undefined
    if (!path?.found || path.geometry.length < 2) {
      source?.setData(EMPTY)
      return
    }
    source?.setData({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: path.geometry },
          properties: {},
        },
      ],
    })
    const bounds = boundsOfCoords(path.geometry)
    if (bounds) map.fitBounds(bounds as LngLatBoundsLike, { padding: 80, duration: 600 })
  }, [path, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const source = map.getSource('markers') as GeoJSONSource | undefined
    source?.setData(markerCollection(fromStop, toStop, selectedStop))
  }, [fromStop, toStop, selectedStop, ready])

  return (
    <div className="map-wrap">
      <div className="map" ref={containerRef} data-testid="map" />
      {styleError && (
        <div className="map-overlay map-overlay--error">
          <strong>Basemap failed to load.</strong>
          <span>
            The tram network still renders on top of a blank background. ({styleError})
          </span>
        </div>
      )}
    </div>
  )
}
