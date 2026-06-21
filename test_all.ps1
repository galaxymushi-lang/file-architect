$ErrorActionPreference = "Stop"
$pass = 0; $fail = 0

function Upload($path, $name) {
    $b = [System.Guid]::NewGuid().ToString()
    $fb = [System.IO.File]::ReadAllBytes($path)
    $hb = [System.Text.Encoding]::UTF8.GetBytes("--$b`r`nContent-Disposition: form-data; name=`"file`"; filename=`"$name`"`r`nContent-Type: application/octet-stream`r`n`r`n")
    $fb2 = [System.Text.Encoding]::UTF8.GetBytes("`r`n--$b--`r`n")
    $ab = New-Object byte[] ($hb.Length + $fb.Length + $fb2.Length)
    [System.Buffer]::BlockCopy($hb, 0, $ab, 0, $hb.Length)
    [System.Buffer]::BlockCopy($fb, 0, $ab, $hb.Length, $fb.Length)
    [System.Buffer]::BlockCopy($fb2, 0, $ab, $hb.Length + $fb.Length, $fb2.Length)
    $r = [System.Net.HttpWebRequest]::Create("http://localhost:5000/api/upload")
    $r.Method = "POST"; $r.ContentType = "multipart/form-data; boundary=$b"; $r.Timeout = 30000
    $s = $r.GetRequestStream(); $s.Write($ab, 0, $ab.Length); $s.Close()
    $rp = $r.GetResponse(); $rd = New-Object System.IO.StreamReader($rp.GetResponseStream())
    $j = $rd.ReadToEnd() | ConvertFrom-Json; $rd.Close(); $rp.Close()
    return $j
}

function Post($url, $data) {
    $b = [System.Text.Encoding]::UTF8.GetBytes($data)
    $r = [System.Net.HttpWebRequest]::Create($url)
    $r.Method = "POST"; $r.ContentType = "application/json"; $r.Timeout = 60000
    $s = $r.GetRequestStream(); $s.Write($b, 0, $b.Length); $s.Close()
    $rp = $r.GetResponse(); $rd = New-Object System.IO.StreamReader($rp.GetResponseStream())
    $j = $rd.ReadToEnd() | ConvertFrom-Json; $rd.Close(); $rp.Close()
    return $j
}

function Chat($fn, $msg) {
    $data = @{messages=@(@{role="user";content=$msg});filename=$fn} | ConvertTo-Json -Depth 3
    $b = [System.Text.Encoding]::UTF8.GetBytes($data)
    $r = [System.Net.HttpWebRequest]::Create("http://localhost:5000/api/ai/chat")
    $r.Method = "POST"; $r.ContentType = "application/json"; $r.Timeout = 60000
    $s = $r.GetRequestStream(); $s.Write($b, 0, $b.Length); $s.Close()
    $rp = $r.GetResponse(); $rd = New-Object System.IO.StreamReader($rp.GetResponseStream())
    $full = ""
    while (-not $rd.EndOfStream) {
        $line = $rd.ReadLine()
        if ($line -and $line.StartsWith("data: ") -and $line -notmatch "\[DONE\]") {
            try { $j = $line.Substring(6) | ConvertFrom-Json; if ($j.token) { $full += $j.token } } catch {}
        }
    }
    $rd.Close(); $rp.Close()
    return $full
}

function T($name, $ok) {
    if ($ok) { Write-Host "  [PASS] $name" -ForegroundColor Green; $script:pass++ }
    else { Write-Host "  [FAIL] $name" -ForegroundColor Red; $script:fail++ }
}

$u = "C:\Users\hp\file-architect\uploads"

# ===== CREATE FILES =====
"Hello World`nTest document`nGALACTOS AI" | Out-File "$u\test.txt" -Encoding UTF8
"Name,Salary`nJohn,85000`nSarah,72000" | Out-File "$u\test.csv" -Encoding UTF8

# ===== TXT =====
Write-Host "`n=== TXT ===" -ForegroundColor Cyan
$r = Upload "$u\test.txt" "test.txt"
T "TXT Upload" ($r.success -eq $true)
$fn = $r.filename

$r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
T "TXT Extract" ($null -ne $r.text -and $r.text.Length -gt 0)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pdf`"}"
T "TXT->PDF" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"docx`"}"
T "TXT->DOCX" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"xlsx`"}"
T "TXT->XLSX" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pptx`"}"
T "TXT->PPTX" ($r.success -eq $true)

$r = Chat $fn "What is this file?"
T "TXT Chat" ($r.Length -gt 5)

# ===== CSV =====
Write-Host "`n=== CSV ===" -ForegroundColor Cyan
$r = Upload "$u\test.csv" "test.csv"
T "CSV Upload" ($r.success -eq $true)
$fn = $r.filename

$r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
T "CSV Extract" ($null -ne $r.data -or $null -ne $r.text)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pdf`"}"
T "CSV->PDF" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"xlsx`"}"
T "CSV->XLSX" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"txt`"}"
T "CSV->TXT" ($r.success -eq $true)

$r = Chat $fn "List employees"
T "CSV Chat" ($r.Length -gt 5)

# ===== XLSX =====
Write-Host "`n=== XLSX ===" -ForegroundColor Cyan
$xl = New-Object -ComObject Excel.Application; $xl.Visible = $false
$wb = $xl.Workbooks.Add(); $ws = $wb.Worksheets.Item(1)
$ws.Cells.Item(1,1)="Name"; $ws.Cells.Item(1,2)="Score"
$ws.Cells.Item(2,1)="Alice"; $ws.Cells.Item(2,2)=95
$ws.Cells.Item(3,1)="Bob"; $ws.Cells.Item(3,2)=87
$wb.SaveAs("$u\test.xlsx"); $wb.Close(); $xl.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null

$r = Upload "$u\test.xlsx" "test.xlsx"
T "XLSX Upload" ($r.success -eq $true)
$fn = $r.filename

$r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
T "XLSX Extract" ($null -ne $r.sheets)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pdf`"}"
T "XLSX->PDF" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"csv`"}"
T "XLSX->CSV" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"txt`"}"
T "XLSX->TXT" ($r.success -eq $true)

$r = Chat $fn "What data is here?"
T "XLSX Chat" ($r.Length -gt 5)

# ===== XLS =====
Write-Host "`n=== XLS (OLD) ===" -ForegroundColor Cyan
$xl = New-Object -ComObject Excel.Application; $xl.Visible = $false
$wb = $xl.Workbooks.Add(); $ws = $wb.Worksheets.Item(1)
$ws.Cells.Item(1,1)="Product"; $ws.Cells.Item(1,2)="Price"
$ws.Cells.Item(2,1)="Widget"; $ws.Cells.Item(2,2)=25
$ws.Cells.Item(3,1)="Gadget"; $ws.Cells.Item(3,2)=50
$wb.SaveAs("$u\test.xls", 56); $wb.Close(); $xl.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null

$r = Upload "$u\test.xls" "test.xls"
T "XLS Upload" ($r.success -eq $true)
$fn = $r.filename

$r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
T "XLS Extract" ($null -ne $r.sheets)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pdf`"}"
T "XLS->PDF" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"csv`"}"
T "XLS->CSV" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"txt`"}"
T "XLS->TXT" ($r.success -eq $true)

$r = Chat $fn "What products?"
T "XLS Chat" ($r.Length -gt 5)

# ===== DOCX =====
Write-Host "`n=== DOCX ===" -ForegroundColor Cyan
$wd = New-Object -ComObject Word.Application; $wd.Visible = $false
$doc = $wd.Documents.Add()
$doc.Content.Text = "Test document for GALACTOS.`n`nMultiple paragraphs here."
$doc.SaveAs("$u\test.docx", 16); $doc.Close(); $wd.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($wd) | Out-Null

$r = Upload "$u\test.docx" "test.docx"
T "DOCX Upload" ($r.success -eq $true)
$fn = $r.filename

$r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
T "DOCX Extract" ($null -ne $r.text -and $r.text.Length -gt 0)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pdf`"}"
T "DOCX->PDF" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"txt`"}"
T "DOCX->TXT" ($r.success -eq $true)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"pptx`"}"
T "DOCX->PPTX" ($r.success -eq $true)

$r = Chat $fn "Summarize this"
T "DOCX Chat" ($r.Length -gt 5)

# ===== PPTX =====
Write-Host "`n=== PPTX ===" -ForegroundColor Cyan
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Add()
$s1 = $pres.Slides.Add(1, 1)
$s1.Shapes.Title.TextFrame.TextRange.Text = "GALACTOS Test"
$pres.SaveAs("$u\test.pptx"); $pres.Close(); $pp.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp) | Out-Null

$r = Upload "$u\test.pptx" "test.pptx"
T "PPTX Upload" ($r.success -eq $true)
$fn = $r.filename

$r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
T "PPTX Extract" ($null -ne $r.text -or $null -ne $r.slides)

$r = Post "http://localhost:5000/api/convert" "{`"filename`":`"$fn`",`"target_format`":`"txt`"}"
T "PPTX->TXT" ($r.success -eq $true)

$r = Chat $fn "What slides?"
T "PPTX Chat" ($r.Length -gt 5)

# ===== PDF =====
Write-Host "`n=== PDF ===" -ForegroundColor Cyan
$pdfs = Get-ChildItem "C:\Users\hp\file-architect\outputs\*converted.pdf" -ErrorAction SilentlyContinue
if ($pdfs) {
    Copy-Item $pdfs[0].FullName "$u\test_for_pdf.pdf" -Force
    $r = Upload "$u\test_for_pdf.pdf" "test_for_pdf.pdf"
    T "PDF Upload" ($r.success -eq $true)
    $fn = $r.filename
    
    $r = Post "http://localhost:5000/api/extract" "{`"filename`":`"$fn`"}"
    T "PDF Extract" ($null -ne $r.text -and $r.text.Length -gt 0)
    
    $r = Chat $fn "What is in this PDF?"
    T "PDF Chat" ($r.Length -gt 5)
} else { Write-Host "  [SKIP] No PDF" -ForegroundColor Yellow }

# ===== AI TOOLS =====
Write-Host "`n=== AI TOOLS ===" -ForegroundColor Cyan
$firstFn = (Upload "$u\test.txt" "aiml.txt").filename
$r = Post "http://localhost:5000/api/ai/summarize" "{`"filename`":`"$firstFn`"}"
T "AI Summarize" ($null -ne $r.summary -and $r.summary.Length -gt 5)

$r = Post "http://localhost:5000/api/ai/extract_smart" "{`"filename`":`"$firstFn`",`"extract_type`":`"entities`"}"
T "AI Extract Smart" ($null -ne $r.extracted -and $r.extracted.Length -gt 5)

# ===== MULTI-CHAT =====
Write-Host "`n=== MULTI-CHAT ===" -ForegroundColor Cyan
$r1 = Chat $firstFn "My name is TestUser"
T "Chat msg 1" ($r1.Length -gt 3)

$r2 = Chat $firstFn "What is my name?"
T "Chat msg 2" ($r2.Length -gt 3)

$r3 = Chat $firstFn "Tell me a joke"
T "Chat msg 3" ($r3.Length -gt 3)

# ===== SUMMARY =====
Write-Host "`n========================================" -ForegroundColor White
Write-Host "  RESULTS: $pass PASSED, $fail FAILED" -ForegroundColor $(if ($fail -eq 0) {"Green"} else {"Red"})
Write-Host "========================================" -ForegroundColor White
