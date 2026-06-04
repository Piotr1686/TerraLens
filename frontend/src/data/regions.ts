export interface Region {
  id: string
  label: string
  longitude: number
  latitude: number
  zoom: number
  bbox: [number, number, number, number]  // [west, south, east, north]
}

export const REGIONS: Region[] = [
  { id: 'amazonia', label: 'Amazonia', longitude: -60, latitude: -5,  zoom: 4, bbox: [-80, -20, -40,  10] },
  { id: 'dubai',    label: 'Dubai',    longitude: 55.3, latitude: 25.2, zoom: 5, bbox: [ 50,  20,  60,  30] },
  { id: 'arctic',   label: 'Arctic',   longitude: 15,   latitude: 72,  zoom: 3, bbox: [-30,  60,  60,  82] },
]
