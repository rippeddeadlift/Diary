$root = (Get-Location).Path
$appData = Join-Path $root "data"
$mediaData = if ($env:DIARY_MEDIA_DIR) { $env:DIARY_MEDIA_DIR } else { "E:\Diary\data" }
$inbox = Join-Path $mediaData "photos\inbox"
$thumbs = Join-Path $appData "photos\_thumbs"

Get-ChildItem $inbox -Recurse -File |
  Where-Object { $_.Extension -in ".mp4", ".mov", ".m4v", ".webm" } |
  ForEach-Object {
    $relative = $_.FullName.Substring($mediaData.Length + 1)
    $output = Join-Path $thumbs ([IO.Path]::ChangeExtension($relative, ".jpg"))

    if (-not (Test-Path $output)) {
      New-Item -ItemType Directory -Force -Path (Split-Path $output) | Out-Null
      ffmpeg -hide_banner -loglevel error -y -ss 0.5 -i $_.FullName `
        -frames:v 1 -vf "scale=512:512:force_original_aspect_ratio=increase,crop=512:512" $output
      if ($LASTEXITCODE -eq 0) { "Created $output" } else { "Failed: $($_.FullName)" }
    }
  }