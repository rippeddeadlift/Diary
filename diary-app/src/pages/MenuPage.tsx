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
    <button onClick={onClick} className="text-left">
      <Card className="transition hover:shadow-md">
        <CardHeader>
          <CardTitle className="text-2xl tracking-wide">{title}</CardTitle>
          <CardDescription className="text-base">{desc}</CardDescription>
        </CardHeader>
      </Card>
    </button>
  )
}
