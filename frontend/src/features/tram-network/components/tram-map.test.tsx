import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"

const renderer = vi.hoisted(() => ({ fail: false, instances: [] as Array<Record<string, unknown>> }))
vi.mock("maplibre-gl", () => {
  class Map {
    listeners: Record<string, () => void> = {}
    canvas = document.createElement("canvas")
    constructor() {
      if (renderer.fail) throw new Error("WebGL unavailable")
      renderer.instances.push(this as unknown as Record<string, unknown>)
    }
    on(name: string, callback: () => void) { this.listeners[name] = callback }
    addControl() {}
    getCanvas() { return this.canvas }
    remove() {}
  }
  class Control {}
  class Popup { remove() {} }
  return { MapLibreMap: Map, NavigationControl: Control, ScaleControl: Control,
    AttributionControl: Control, Popup, setWorkerUrl: vi.fn() }
})

import { TramMap } from "./tram-map"
import type { TramGraphGeoJson } from "../types"

const network: TramGraphGeoJson = { type: "FeatureCollection", metadata: { missing_geometry_edges: 0, synthetic: false }, features: [
  { type: "Feature", geometry: { type: "Point", coordinates: [37.6, 55.7] },
    properties: { id: 101, name: "Остановка А", routes: ["1"] } },
  { type: "Feature", geometry: { type: "LineString", coordinates: [[37.6, 55.7], [37.7, 55.8]] },
    properties: { geometry_quality: "provided", source: 101, target: 102, length_m: 400, routes: ["1"] } },
] }
const defaults = { network, routeGeoJson: undefined, selectedRoute: null, path: undefined,
  fromStop: null, toStop: null, selectedStop: null }
beforeEach(() => { renderer.fail = false; renderer.instances = [] })
afterEach(cleanup)

it("keeps a selectable committed graph when WebGL initialization fails and retries", async () => {
  renderer.fail = true
  const onStopClick = vi.fn()
  render(<TramMap {...defaults} onStopClick={onStopClick} />)
  await screen.findByText(/Карта недоступна/)
  expect(screen.queryByText(/сеть отрисована/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByText("Остановки и участки сети"))
  fireEvent.click(screen.getByRole("button", { name: "Остановка А · OSM 101" }))
  expect(onStopClick).toHaveBeenCalledWith(101)
  expect(screen.getByText(/OSM 101 → OSM 102/)).toBeInTheDocument()
  renderer.fail = false
  fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку карты" }))
  await waitFor(() => expect(screen.getByTestId("tram-map")).toHaveAttribute("data-state", "loading"))
  expect(renderer.instances).toHaveLength(1)
})

it("reports every renderer error truthfully, including generic style network failures", () => {
  render(<TramMap {...defaults} onStopClick={vi.fn()} />)
  const listeners = renderer.instances[0].listeners as Record<string, () => void>
  act(() => listeners.error())
  expect(screen.getByTestId("tram-map")).toHaveAttribute("data-state", "unavailable")
  expect(screen.getByText(/Карта недоступна/)).toBeInTheDocument()
})

it("exposes missing and synthetic geometry without hover", () => {
  renderer.fail = true
  const partial: TramGraphGeoJson = { ...network,
    metadata: { missing_geometry_edges: 1, synthetic: true },
    features: network.features.map((feature) => "source" in feature.properties
      ? { ...feature, properties: { ...feature.properties, geometry_quality: "inferred" as const } }
      : feature) as TramGraphGeoJson["features"] }
  render(<TramMap {...defaults} network={partial} onStopClick={vi.fn()} />)
  expect(screen.getByText(/Прямые соединения не показаны как рельсы/)).toBeInTheDocument()
  expect(screen.getByText(/Синтетическая геометрия/)).toBeInTheDocument()
  expect(screen.getByText(/OSM 101 → OSM 102.*геометрия отсутствует/)).toBeInTheDocument()
})
