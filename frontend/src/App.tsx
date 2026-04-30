import { useCallback, useState } from 'react'
import { Globe } from '@/components/Globe'
import { Timeline } from '@/components/Timeline'
import { HeatmapControls } from '@/components/HeatmapControls'
import { useTimeline } from '@/hooks/useTimeline'
import { useHeatmapLayer } from '@/hooks/useHeatmapLayer'
import type { HeatmapMetric } from '@/hooks/useHeatmapLayer'

function App() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [manifestTimeline, setManifestTimeline] = useState<string[] | undefined>()
  const [heatmapMetric, setHeatmapMetric] = useState<HeatmapMetric>('ndvi')
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6)

  const handleManifestLoaded = useCallback((manifest: unknown) => {
    const m = manifest as { timeline?: string[] }
    if (Array.isArray(m?.timeline)) setManifestTimeline(m.timeline)
  }, [])

  const { dates, dateIndex, currentDate, tileUrl, setDateIndex } = useTimeline(manifestTimeline)

  const heatmapLayer = useHeatmapLayer({
    region: selectedRegion,
    metric: heatmapMetric,
    opacity: heatmapOpacity,
    currentDate,
  })

  return (
    <div className="h-full w-full">
      <Globe
        tileUrl={tileUrl}
        extraLayers={heatmapLayer ? [heatmapLayer] : []}
        onRegionSelect={setSelectedRegion}
        onManifestLoaded={handleManifestLoaded}
      />
      <Timeline dates={dates} dateIndex={dateIndex} onDateChange={setDateIndex} />
      <HeatmapControls
        metric={heatmapMetric}
        opacity={heatmapOpacity}
        onMetricChange={setHeatmapMetric}
        onOpacityChange={setHeatmapOpacity}
      />
      {selectedRegion && (
        <div className="absolute left-4 top-4 rounded bg-black/50 px-3 py-1 text-sm text-white backdrop-blur">
          {selectedRegion}
        </div>
      )}
    </div>
  )
}

export default App
