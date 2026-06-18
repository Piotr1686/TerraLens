import { useCallback, useEffect, useMemo, useState } from 'react'
import { Globe } from '@/components/Globe'
import { Starfield } from '@/components/Starfield'
import { SearchBox } from '@/components/SearchBox'
import { ExploreControls } from '@/components/ExploreControls'
import { REGIONS } from '@/data/regions'
import { ArrivalRing } from '@/components/ArrivalRing'
import { RegionHUD } from '@/components/RegionHUD'
import { Timeline } from '@/components/Timeline'
import { HeatmapControls } from '@/components/HeatmapControls'
import { StatsPanel } from '@/components/StatsPanel'
import { SuperResPanel } from '@/components/SuperResPanel'
import { GuidedTour } from '@/components/GuidedTour'
import { Preloader } from '@/components/Preloader'
import { useTimeline } from '@/hooks/useTimeline'
import { useHeatmapLayer } from '@/hooks/useHeatmapLayer'
import { usePMTilesLayer } from '@/hooks/usePMTilesLayer'
import { useTour } from '@/hooks/useTour'
import { usePreload } from '@/hooks/usePreload'
import { useRevealOpacity } from '@/hooks/useRevealOpacity'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { useExploreScenes, useExploreLayer } from '@/hooks/useExploreLayer'
import { useExploreSelection } from '@/hooks/useExploreSelection'
import type { HeatmapMetric } from '@/hooks/useHeatmapLayer'
import type { GeocodeResult } from '@/lib/geocode'

function App() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [arrivedRegion, setArrivedRegion] = useState<string | null>(null)
  const [manifestTimeline, setManifestTimeline] = useState<string[] | undefined>()
  const [heatmapMetric, setHeatmapMetric] = useState<HeatmapMetric>('ndvi')
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6)
  const [viewportZoom, setViewportZoom] = useState(1.0)

  // Tryb Explore (S10 WS3) — wyszukiwanie dowolnego miejsca + warstwa Sentinel-2 (MPC).
  const [exploreTarget, setExploreTarget] = useState<{ lon: number; lat: number } | null>(null)
  const [flyCoords, setFlyCoords] = useState<{ longitude: number; latitude: number; zoom: number } | null>(null)

  const isMobile = useMediaQuery('(max-width: 768px)')
  const fps = isMobile ? 30 : 60

  const { progress, label, isReady, manifest, hasPreview } = usePreload()

  // Tour startuje dopiero po zakończeniu preloadera
  const { isRunning, isComplete, stepIndex, currentStep, stop, replay } = useTour({ enabled: isReady })

  // Manifest z usePreload → timeline
  useEffect(() => {
    if (!manifest) return
    const m = manifest as { timeline?: string[] }
    if (Array.isArray(m?.timeline)) setManifestTimeline(m.timeline)
  }, [manifest])

  // Synchronizacja selectedRegion z aktywnym krokiem trasy
  useEffect(() => {
    if (!isRunning) return
    setSelectedRegion(currentStep?.regionId ?? null)
  }, [currentStep, isRunning])

  // Nowy lot (selectedRegion zmienia się) → chowamy heatmapę; pokaże się po arrival
  useEffect(() => {
    setArrivedRegion(null)
  }, [selectedRegion])

  // Kliknięcie markera przez usera przerywa tour
  const handleRegionSelect = useCallback(
    (regionId: string | null) => {
      if (isRunning) stop()
      setSelectedRegion(regionId)
    },
    [isRunning, stop],
  )

  // Globe wywołuje po wylądowaniu kamery → trigger dla reveal animacji
  const handleRegionArrival = useCallback((regionId: string) => {
    setArrivedRegion(regionId)
  }, [])

  const revealFraction = useRevealOpacity(arrivedRegion, 600, fps)

  const { dates, dateIndex, tileUrl, setDateIndex } = useTimeline(manifestTimeline)

  // PMTiles to snapshot "latest". Przy scrubbingu/timelapse w przeszłość chowamy go,
  // żeby odsłonić historyczną teksturę MODIS regionu (base tileUrl zależny od daty).
  const isLatestDate = dates.length === 0 || dateIndex === dates.length - 1

  const arrivedBbox = arrivedRegion
    ? REGIONS.find((r) => r.id === arrivedRegion)?.bbox
    : undefined

  const HF_BASE = 'https://huggingface.co/datasets/Piotr1686/terralens-data/resolve/main'

  const pmtilesUrl = useMemo(() => {
    if (!arrivedRegion || !manifest) return null
    const m = manifest as { regions?: Record<string, { latest?: string }> }
    const latest = m?.regions?.[arrivedRegion]?.latest
    return latest ? `${HF_BASE}/${latest}` : null
  }, [arrivedRegion, manifest])

  const pmtilesLayers = usePMTilesLayer({
    region: arrivedRegion,
    pmtilesUrl,
    opacity: 0.9 * revealFraction * (isLatestDate ? 1 : 0),
    bbox: arrivedBbox,
    viewportZoom,
  })

  const heatmapLayers = useHeatmapLayer({
    region: arrivedRegion,
    metric: heatmapMetric,
    opacity: heatmapOpacity * revealFraction,
    bbox: arrivedBbox,
  })

  const { scenes: exploreScenes, status: exploreStatus, retry: exploreRetry } = useExploreScenes(exploreTarget)
  const exploreSel = useExploreSelection(exploreScenes)
  const exploreScene = exploreSel.scene
  const exploreLayers = useExploreLayer({ scene: exploreScene })

  // Cap kamery per źródło — odrobina headroomu nad natywnym sufitem kafli (NAIP z18, S2 z14).
  const exploreMaxZoom = exploreScene ? exploreScene.maxZoom + 0.5 : 16

  // Wyszukiwarka → wejście w tryb Explore nad punktem (przerywa tour i czyści region).
  const handleSearchSelect = useCallback(
    (r: GeocodeResult) => {
      if (isRunning) stop()
      setSelectedRegion(null)
      setArrivedRegion(null)
      setExploreTarget({ lon: r.lon, lat: r.lat })
      setFlyCoords({ longitude: r.lon, latitude: r.lat, zoom: 13 })
    },
    [isRunning, stop],
  )

  const handleSearchClear = useCallback(() => {
    setExploreTarget(null)
    setFlyCoords({ longitude: 0, latitude: 20, zoom: 1.0 })
  }, [])

  const flyTarget = isRunning ? (currentStep?.regionId ?? null) : undefined

  const arrivedRegionObj = arrivedRegion
    ? REGIONS.find((r) => r.id === arrivedRegion) ?? null
    : null

  return (
    <div className="relative h-full w-full overflow-hidden bg-black">
      <Starfield />
      <Globe
        tileUrl={tileUrl}
        extraLayers={[...pmtilesLayers, ...heatmapLayers, ...exploreLayers]}
        flyTarget={flyTarget}
        flyToCoords={flyCoords}
        maxZoom={exploreMaxZoom}
        onRegionSelect={handleRegionSelect}
        onRegionArrival={handleRegionArrival}
        onViewZoomChange={setViewportZoom}
        fps={fps}
      />
      <SearchBox onSelect={handleSearchSelect} onClear={handleSearchClear} active={!!exploreTarget} />
      {exploreTarget && (
        <div className="absolute bottom-6 right-4 max-w-xs rounded-xl bg-black/50 px-4 py-3 text-xs backdrop-blur">
          {exploreStatus === 'loading' && <p className="text-white/60">Finding imagery here…</p>}
          {exploreStatus === 'empty' && <p className="text-amber-300/80">No imagery available here.</p>}
          {exploreStatus === 'error' && (
            <div className="flex items-center gap-3">
              <p className="text-amber-300/80">Imagery service is busy.</p>
              <button
                onClick={exploreRetry}
                className="rounded-lg bg-white/10 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-white/20"
              >
                Retry
              </button>
            </div>
          )}
          {exploreStatus === 'ready' && exploreScene && <p className="text-white/60">{exploreScene.label}</p>}
        </div>
      )}
      {exploreTarget && exploreStatus === 'ready' && (
        <ExploreControls
          source={exploreSel.source}
          onSourceChange={exploreSel.setSource}
          hasNaip={exploreSel.hasNaip}
          clearOnly={exploreSel.clearOnly}
          onClearOnlyChange={exploreSel.setClearOnly}
          available={exploreSel.available}
          dateIndex={exploreSel.dateIndex}
          onDateIndexChange={exploreSel.setDateIndex}
        />
      )}
      {arrivedRegion && <ArrivalRing key={arrivedRegion} />}
      <RegionHUD region={arrivedRegionObj} />
      <GuidedTour
        isRunning={isRunning}
        isComplete={isComplete}
        stepIndex={stepIndex}
        currentStep={currentStep}
        onStop={stop}
        onReplay={replay}
      />
      {!exploreTarget && <Timeline dates={dates} dateIndex={dateIndex} onDateChange={setDateIndex} showPlay={!!arrivedRegion} />}
      {arrivedRegion && (
        <HeatmapControls
          metric={heatmapMetric}
          opacity={heatmapOpacity}
          onMetricChange={setHeatmapMetric}
          onOpacityChange={setHeatmapOpacity}
        />
      )}
      <StatsPanel regionId={selectedRegion} />
      <SuperResPanel regionId={arrivedRegion} />
      <Preloader progress={progress} label={label} isReady={isReady} hasPreview={hasPreview} />
    </div>
  )
}

export default App
