import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { ForecastHorizon, ForecastPoint } from "@/features/forecast/types"
import { formatPassengers } from "@/lib/utils"

const horizonTitles: Record<ForecastHorizon, string> = {
  day: "Почасовой прогноз",
  month: "Прогноз по дням",
  year: "Прогноз по месяцам",
}

function formatTick(timestamp: string, horizon: ForecastHorizon) {
  const date = new Date(timestamp)
  if (horizon === "day") {
    return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", timeZone: "Europe/Moscow" }).format(date)
  }
  if (horizon === "month") {
    return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", timeZone: "Europe/Moscow" }).format(date)
  }
  return new Intl.DateTimeFormat("ru-RU", { month: "short", timeZone: "Europe/Moscow" }).format(date)
}

interface ForecastChartProps {
  points: readonly ForecastPoint[]
  horizon: ForecastHorizon
}

export function ForecastChart({ points, horizon }: ForecastChartProps) {
  const data = points.map((point) => ({
    ...point,
    label: formatTick(point.timestamp, horizon),
    uncertainty: point.upper_bound - point.lower_bound,
  }))
  const peak = Math.max(...points.map((point) => point.predicted_passengers))

  return (
    <Card className="chart-card">
      <CardHeader className="chart-header">
        <div>
          <CardTitle>{horizonTitles[horizon]}</CardTitle>
          <CardDescription>Поток по сети после распределения на маршрут</CardDescription>
        </div>
        <div className="chart-legend" aria-label="Легенда графика">
          <span><i className="legend-line legend-forecast" />Прогноз</span>
          <span><i className="legend-band" />Интервал неопределённости</span>
          <span><i className="legend-line legend-capacity" />Вместимость</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="chart-wrap" role="img" aria-label={`Пик прогноза ${formatPassengers(peak)} пассажиров`}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="2 4" />
              <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={28} />
              <YAxis tickLine={false} axisLine={false} width={50} />
              <Tooltip
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 13,
                }}
                formatter={(value, name) => [formatPassengers(Number(value)), name === "predicted_passengers" ? "Прогноз" : String(name)]}
              />
              <Area type="monotone" dataKey="lower_bound" stackId="uncertainty" stroke="none" fill="transparent" tooltipType="none" />
              <Area type="monotone" dataKey="uncertainty" stackId="uncertainty" stroke="none" fill="var(--chart-2)" fillOpacity={0.12} tooltipType="none" />
              <Line type="monotone" dataKey="lower_bound" name="Нижняя граница" stroke="transparent" dot={false} activeDot={false} />
              <Line type="monotone" dataKey="upper_bound" name="Верхняя граница" stroke="transparent" dot={false} activeDot={false} />
              <Line type="monotone" dataKey="predicted_passengers" name="Прогноз" stroke="var(--foreground)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: "var(--primary)" }} />
              <Line type="stepAfter" dataKey="capacity" name="Вместимость" stroke="var(--primary)" strokeWidth={1.5} strokeDasharray="6 5" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
