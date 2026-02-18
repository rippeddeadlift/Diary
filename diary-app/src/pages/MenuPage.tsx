export function MenuPage({
  onTours,
  onPhotos,
  onFitness
}: {
  onTours: () => void
  onPhotos: () => void
  onFitness: () => void
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-10 py-10 text-center">
      <MenuItem title="FOTOS" onClick={onPhotos} highlight />
      <MenuItem title="TOUREN" onClick={onTours} />
      <MenuItem title="FITNESS" onClick={onFitness} />
    </div>
  )
}

function MenuItem({
  title,
  onClick,
  highlight
}: {
  title: string
  onClick: () => void
  highlight?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={
        "w-full max-w-xl select-none px-6 py-6 text-4xl font-semibold tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" +
        (highlight ? " text-yellow-500" : "") +
        " hover:text-yellow-500"
      }
    >
      {title}
    </button>
  )
}
