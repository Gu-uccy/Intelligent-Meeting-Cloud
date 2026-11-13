$ErrorActionPreference = "Stop"

$docx = "D:\QQ\总结报告_补图增强版.docx"
$pdf = "D:\Project\Intelligent-Meeting-Cloud\report_render_check\总结报告_补图增强版.pdf"
$outDir = Split-Path -Parent $pdf
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($docx)
    $doc.ExportAsFixedFormat($pdf, 17)
    $doc.Close($false)
}
finally {
    $word.Quit()
}

Write-Output $pdf
