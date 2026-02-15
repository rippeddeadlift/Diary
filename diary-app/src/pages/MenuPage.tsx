import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

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
    <div className="grid gap-4">
      <MenuCard title="FOTOS" desc="" onClick={onPhotos} />
      <MenuCard title="TOUREN" desc="" onClick={onTours} />
      <MenuCard title="FITNESS" desc="" onClick={onFitness} />
    </div>
  )
}

function MenuCard({ title, desc, onClick }: { title: string; desc: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-center">
      <Card className="border-0 transition-all duration-200 ease-out hover:shadow-md hover:scale-[1.5]  hover:text-yellow-500 cursor-default">
        <CardHeader className="py-10">
          <CardTitle className="text-3xl tracking-wide">{title}</CardTitle>
          <CardDescription className="mx-auto mt-2 max-w-[28ch] text-base">{desc}</CardDescription>
        </CardHeader>
      </Card>
    </button>
  )
}
