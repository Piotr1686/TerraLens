import { useCallback, useState } from 'react'
import { Globe } from '@/components/Globe'
import { Timeline } from '@/components/Timeline'
import { useTimeline } from '@/hooks/useTimeline'

function App() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [manifestTimeline, setManifestTimeline] = useState<string[] | undefined>()

  const handleManifestLoaded = useCallback((manifest: unknown) => {
    const m = manifest as { timeline?: string[] }
    if (Array.isArray(m?.timeline)) setManifestTimeline(m.timeline)
  }, [])

  const { dates, dateIndex, tileUrl, setDateIndex } = useTimeline(manifestTimeline)

  return (
    <div className="h-full w-full">
      <Globe
        tileUrl={tileUrl}
        onRegionSelect={setSelectedRegion}
        onManifestLoaded={handleManifestLoaded}
      />
      <Timeline dates={dates} dateIndex={dateIndex} onDateChange={setDateIndex} />
      {selectedRegion && (
        <div className="absolute left-4 top-4 rounded bg-black/50 px-3 py-1 text-sm text-white backdrop-blur">
          {selectedRegion}
        </div>
      )}
    </div>
  )
}

export default App
