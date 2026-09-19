import { ArrowRight, RotateCcw, Sparkles } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useScenario } from "@/features/forecast/hooks/use-forecast"
import type { ForecastHorizon } from "@/features/forecast/types"
import { formatSigned } from "@/lib/utils"

interface ScenarioPanelProps {
  routeId: number
  horizon: ForecastHorizon
}

export function ScenarioPanel({ routeId, horizon }: ScenarioPanelProps) {
  const [vehicles, setVehicles] = useState(2)
  const [interval, setInterval] = useState(-10)
  const [demand, setDemand] = useState(20)
  const scenario = useScenario()

  const runScenario = () => scenario.mutate({
    route_id: routeId,
    horizon,
    additional_vehicles: vehicles,
    interval_change_percent: interval,
    demand_change_percent: demand,
  })

  const reset = () => {
    setVehicles(0)
    setInterval(0)
    setDemand(0)
    scenario.reset()
  }

  return (
    <Card className="scenario-card">
      <CardHeader>
        <div className="scenario-title">
          <span className="scenario-mark"><Sparkles /></span>
          <div>
            <CardTitle>Что будет, если?</CardTitle>
            <CardDescription>Измените сеть и сравните с базовым прогнозом</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="scenario-content">
        <label>
          <span>Дополнительные трамваи <b>{formatSigned(vehicles)}</b></span>
          <input type="range" min="-3" max="10" value={vehicles} onChange={(event) => setVehicles(Number(event.target.value))} />
        </label>
        <label>
          <span>Изменение интервала <b>{formatSigned(interval, "%")}</b></span>
          <input type="range" min="-50" max="100" step="5" value={interval} onChange={(event) => setInterval(Number(event.target.value))} />
        </label>
        <label>
          <span>Импульс спроса / событие <b>{formatSigned(demand, "%")}</b></span>
          <input type="range" min="-50" max="200" step="5" value={demand} onChange={(event) => setDemand(Number(event.target.value))} />
        </label>

        {scenario.data && (
          <div className="scenario-result" aria-live="polite">
            <span>Пиковая загрузка</span>
            <div>
              <strong>{scenario.data.baseline_peak_load_percent.toFixed(0)}%</strong>
              <ArrowRight />
              <strong className={scenario.data.scenario_peak_load_percent >= 100 ? "is-critical" : ""}>
                {scenario.data.scenario_peak_load_percent.toFixed(0)}%
              </strong>
            </div>
            <small>Прототип расчёта · {scenario.data.solver_version}</small>
          </div>
        )}
        {scenario.isError && <p className="inline-error">Не удалось рассчитать сценарий. Повторите запрос.</p>}

        <div className="scenario-actions">
          <Button onClick={runScenario} disabled={scenario.isPending}>
            {scenario.isPending ? "Считаем…" : "Рассчитать сценарий"}
          </Button>
          <Button variant="ghost" size="icon" onClick={reset} aria-label="Сбросить сценарий">
            <RotateCcw />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
