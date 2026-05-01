import { useCallback, useEffect, useState } from 'react'
import { Globe } from '@/components/Globe'
import { Timeline } from '@/components/Timeline'
import { HeatmapControls } from '@/components/HeatmapControls'
import { StatsPanel } from '@/components/StatsPanel'
import { GuidedTour } from '@/components/GuidedTour'
import { useTimeline } from '@/hooks/useTimeline'
import { useHeatmapLayer } from '@/hooks/useHeatmapLayer'
import { useTour } from '@/hooks/useTour'
import type { HeatmapMetric } from '@/hooks/useHeatmapLayer'

function App() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [manifestTimeline, setManifestTimeline] = useState<string[] | undefined>()
  const [heatmapMetric, setHeatmapMetric] = useState<HeatmapMetric>('ndvi')
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6)

  const { isRunning, isComplete, stepIndex, steps, currentStep, stop, replay } = useTour()

  // Synchronizacja selectedRegion z aktywnym krokiem trasy
  useEffect(() => {
    if (!isRunning) return
    setSelectedRegion(currentStep?.regionId ?? null)
  }, [currentStep, isRunning])

  const handleManifestLoaded = useCallback((manifest: unknown) => {
    const m = manifest as { timeline?: string[] }
    if (Array.isArray(m?.timeline)) setManifestTimeline(m.timeline)
  }, [])

  // Kliknięcie markera przez usera przerywa tour
  const handleRegionSelect = useCallback(
    (regionId: string | null) => {
      if (isRunning) stop()
      setSelectedRegion(regionId)
    },
    [isRunning, stop],
  )

  const { dates, dateIndex, currentDate, tileUrl, setDateIndex } = useTimeline(manifestTimeline)

  const heatmapLayer = useHeatmapLayer({
    region: selectedRegion,
    metric: heatmapMetric,
    opacity: heatmapOpacity,
    currentDate,
  })

  // flyTarget: gdy tour działa — steruj globem krokiem; gdy nie — undefined (user kontroluje)
  const flyTarget = isRunning ? (currentStep?.regionId ?? null) : undefined

  return (
    <div className="h-full w-full">
      <Globe
        tileUrl={tileUrl}
        extraLayers={heatmapLayer ? [heatmapLayer] : []}
        flyTarget={flyTarget}
        onRegionSelect={handleRegionSelect}
        onManifestLoaded={handleManifestLoaded}
      />
      <GuidedTour
        isRunning={isRunning}
        isComplete={isComplete}
        stepIndex={stepIndex}
        currentStep={currentStep}
        onStop={stop}
        onReplay={replay}
      />
      <Timeline dates={dates} dateIndex={dateIndex} onDateChange={setDateIndex} />
      <HeatmapControls
        metric={heatmapMetric}
        opacity={heatmapOpacity}
        onMetricChange={setHeatmapMetric}
        onOpacityChange={setHeatmapOpacity}
      />
      <StatsPanel regionId={selectedRegion} dateIndex={dateIndex} />
    </div>
  )
}

export default App
