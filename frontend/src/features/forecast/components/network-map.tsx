import { CircleDot, TrainFront } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { StopLoad } from "@/features/forecast/types"
import { formatPassengers } from "@/lib/utils"

interface NetworkMapProps {
  stops: readonly StopLoad[]
}

function stopColor(load: number) {
  if (load >= 95) return "var(--destructive)"
  if (load >= 75) return "var(--warning)"
  return "var(--chart-2)"
}

export function NetworkMap({ stops }: NetworkMapProps) {
  if (stops.length === 0) {
    return (
      <Card className="map-card">
        <CardHeader><CardTitle>Поток по транспортному графу</CardTitle></CardHeader>
        <CardContent><p className="inline-error">Для выбранного среза нет узлов сети.</p></CardContent>
      </Card>
    )
  }
  const maxLoad = Math.max(...stops.map((stop) => stop.load_percent), 1)
  const longitudes = stops.map((stop) => stop.longitude)
  const latitudes = stops.map((stop) => stop.latitude)
  const minLongitude = Math.min(...longitudes)
  const maxLongitude = Math.max(...longitudes)
  const minLatitude = Math.min(...latitudes)
  const maxLatitude = Math.max(...latitudes)
  const longitudeSpan = maxLongitude - minLongitude || 1
  const latitudeSpan = maxLatitude - minLatitude || 1
  const points = stops.map((stop) => ({
    ...stop,
    x: 10 + ((stop.longitude - minLongitude) / longitudeSpan) * 80,
    y: 64 - ((stop.latitude - minLatitude) / latitudeSpan) * 50,
  }))
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ")

  return (
    <Card className="map-card">
      <CardHeader className="map-header">
        <div>
          <CardTitle>Поток по транспортному графу</CardTitle>
          <CardDescription>Узлы связаны, нагрузка соседних участков учитывается совместно</CardDescription>
        </div>
        <Badge>географический граф</Badge>
      </CardHeader>
      <CardContent className="map-content">
        <div className="network-canvas">
          <div className="map-grid" aria-hidden="true" />
          <svg viewBox="0 0 100 76" role="img" aria-label="Схема остановок выбранного маршрута">
            <path d={path} fill="none" stroke="var(--foreground)" strokeWidth="1.2" strokeLinecap="round" />
            {points.map((point) => (
              <g key={point.id}>
                <circle cx={point.x} cy={point.y} r={4 + (point.load_percent / maxLoad) * 2.5} fill="var(--card)" stroke={stopColor(point.load_percent)} strokeWidth="2" />
                <circle cx={point.x} cy={point.y} r="1.5" fill={stopColor(point.load_percent)} />
              </g>
            ))}
          </svg>
          <div className="map-watermark">МОСКВА · СЕТЬ</div>
        </div>
        <ol className="stop-list" aria-label="Загрузка остановок">
          {stops.map((stop) => (
            <li key={stop.id}>
              <span className="stop-icon" style={{ color: stopColor(stop.load_percent) }}>
                {stop.sequence === 1 ? <TrainFront /> : <CircleDot />}
              </span>
              <span className="stop-name">{stop.name}</span>
              <span className="stop-value">{formatPassengers(stop.predicted_passengers)} · {stop.load_percent.toFixed(0)}%</span>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  )
}
