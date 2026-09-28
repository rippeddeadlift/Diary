import type { FEATURE_ITEMS, FeatureId } from './registry'

export function HomePage({
  features,
  onSelect
}: {
  features: typeof FEATURE_ITEMS
  onSelect: (feature: FeatureId) => void
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-10 py-10 text-center overflow-hidden">
      {features.map((feature) => (
        <HomeMenuItem key={feature.id} title={feature.label.toUpperCase()} onClick={() => onSelect(feature.id)} />
      ))}
    </div>
  )
}

function HomeMenuItem({
  title,
  onClick
}: {
  title: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={
        "w-full max-w-xl select-none px-8 py-8 text-5xl tracking-wide leading-none transition-transform transition-colors duration-200 ease-out transform-gpu hover:scale-125 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 hover:text-yellow-500"
      }
    >
      {title}
    </button>
  )
}
