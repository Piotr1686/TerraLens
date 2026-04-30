import { Globe } from '@/components/Globe'

function App() {
  return (
    <div className="h-full w-full">
      <Globe onRegionSelect={(id) => console.log('region:', id)} />
    </div>
  )
}

export default App
