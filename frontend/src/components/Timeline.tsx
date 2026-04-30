import { Slider } from '@/components/ui/slider'

interface Props {
  dates: string[]
  dateIndex: number
  onDateChange: (index: number) => void
}

function formatDate(dateStr: string): string {
  const [year, month] = dateStr.split('-')
  const monthNames = ['STY', 'LUT', 'MAR', 'KWI', 'MAJ', 'CZE', 'LIP', 'SIE', 'WRZ', 'PAŹ', 'LIS', 'GRU']
  return `${monthNames[parseInt(month, 10) - 1]} ${year}`
}

export function Timeline({ dates, dateIndex, onDateChange }: Props) {
  if (dates.length === 0) return null

  const firstYear = dates[0].slice(0, 4)
  const lastYear = dates[dates.length - 1].slice(0, 4)

  return (
    <div className="absolute bottom-20 left-1/2 w-[min(600px,90vw)] -translate-x-1/2 rounded-xl bg-black/50 px-5 py-4 backdrop-blur">
      <div className="mb-3 flex items-center justify-between text-xs text-white/50">
        <span>{firstYear}</span>
        <span className="text-base font-semibold text-white">{formatDate(dates[dateIndex])}</span>
        <span>{lastYear}</span>
      </div>
      <Slider
        min={0}
        max={dates.length - 1}
        step={1}
        value={[dateIndex]}
        onValueChange={([i]) => onDateChange(i)}
        className="w-full"
      />
    </div>
  )
}
