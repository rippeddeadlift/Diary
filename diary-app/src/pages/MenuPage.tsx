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
    <div className="flex flex-1 flex-col items-center justify-center gap-10 py-10 text-center overflow-hidden">
      <MenuItem title="FOTOS" onClick={onPhotos} />
      <MenuItem title="TOUREN" onClick={onTours} />
      <MenuItem title="FITNESS" onClick={onFitness} />
    </div>
  )
}

function MenuItem({
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
