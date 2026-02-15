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
      <MenuCard title="TOUREN" desc="GPX, Karte, Notizen" onClick={onTours} />
      <MenuCard title="FOTOS" desc="Galerie (bald), nach Tags/Personen" onClick={onPhotos} />
      <MenuCard title="FITNESS" desc="Dips-Tracking (bald)" onClick={onFitness} />
    </div>
  )
}

function MenuCard({ title, desc, onClick }: { title: string; desc: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-center">
      <Card className="transition hover:shadow-md">
        <CardHeader className="py-10">
          <CardTitle className="text-3xl tracking-wide">{title}</CardTitle>
          <CardDescription className="mx-auto mt-2 max-w-[28ch] text-base">{desc}</CardDescription>
        </CardHeader>
      </Card>
    </button>
  )
}
