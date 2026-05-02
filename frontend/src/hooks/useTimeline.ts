import { useState, useMemo } from 'react'

const HLS_RGB_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/250m/{z}/{y}/{x}.jpg'

const BLUE_MARBLE_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'BlueMarble_NextGeneration/default/500m/{z}/{y}/{x}.jpeg'

// Demo daty — miesięczne klatki 2015 do bieżącego miesiąca
function buildDemoDates(): string[] {
  const dates: string[] = []
  const now = new Date()
  for (let y = 2015; y <= now.getFullYear(); y++) {
    const maxMonth = y === now.getFullYear() ? now.getMonth() + 1 : 12
    for (let m = 1; m <= maxMonth; m++) {
      dates.push(`${y}-${String(m).padStart(2, '0')}-01`)
    }
  }
  return dates
}

function tileUrlForDate(date: string): string {
  // Blue Marble nie ma parametru daty; używamy MODIS dla dat historycznych
  return HLS_RGB_URL.replace('{date}', date)
}

export interface TimelineState {
  dates: string[]
  dateIndex: number
  currentDate: string
  tileUrl: string
  setDateIndex: (i: number) => void
}

export function useTimeline(manifestTimeline?: string[]): TimelineState {
  const dates = useMemo(
    () => (manifestTimeline && manifestTimeline.length > 0 ? manifestTimeline : buildDemoDates()),
    [manifestTimeline],
  )

  const [dateIndex, setDateIndex] = useState(dates.length - 1)

  const currentDate = dates[dateIndex] ?? dates[0]

  // Blue Marble dla pozycji "teraz" (ostatnia data) — wygląda lepiej niż MODIS na zoom globalnym
  const tileUrl = dateIndex === dates.length - 1 ? BLUE_MARBLE_URL : tileUrlForDate(currentDate)

  return { dates, dateIndex, currentDate, tileUrl, setDateIndex }
}
