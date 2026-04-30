import { useState, useMemo } from 'react'

const HLS_RGB_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/250m/{z}/{y}/{x}.jpg'

const BLUE_MARBLE_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/' +
  'BlueMarble_NextGeneration/default/500m/{z}/{y}/{x}.jpeg'

// Demo daty — miesięczne klatki 2015–2024
function buildDemoDates(): string[] {
  const dates: string[] = []
  for (let y = 2015; y <= 2024; y++) {
    for (let m = 1; m <= 12; m++) {
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

  // Blue Marble dla ostatniej daty (placeholder "teraz"), MODIS dla historii
  const tileUrl =
    dateIndex === dates.length - 1 ? BLUE_MARBLE_URL : tileUrlForDate(currentDate)

  return { dates, dateIndex, currentDate, tileUrl, setDateIndex }
}
