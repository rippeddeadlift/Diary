export function UploadProgress({
  done,
  total,
  duplicates
}: {
  done: number
  total: number
  duplicates: number
}) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div className="rounded-lg border bg-muted/20 p-3 text-sm">
      <div>
        Upload: <span className="font-semibold">{done}</span> / {total} ({pct}%)
      </div>
      {duplicates > 0 ? <div className="mt-1 text-xs text-muted-foreground">Duplikate übersprungen: {duplicates}</div> : null}
    </div>
  )
}
