#Requires -Version 5.1
<#
  Multi-tenant auth + isolation verification.
  Exercises dev-login, ownership scoping, IDOR-safe 404s, and public share links.
  Run against the local dockerized backend (proxied through the frontend at :3000).
#>
$ErrorActionPreference = "Stop"
$base = "http://localhost:3000/api/v1"
$pass = 0
$fail = 0

function Check($name, $cond) {
    if ($cond) { Write-Host "  PASS  $name" -ForegroundColor Green; $script:pass++ }
    else       { Write-Host "  FAIL  $name" -ForegroundColor Red;   $script:fail++ }
}

function New-Session { New-Object Microsoft.PowerShell.Commands.WebRequestSession }

function Invoke-Api {
    param($Method, $Path, $Session, $Body, [switch]$Raw)
    $args = @{ Method = $Method; Uri = "$base$Path"; WebSession = $Session; ErrorAction = "Stop" }
    if ($Body) { $args.Body = ($Body | ConvertTo-Json); $args.ContentType = "application/json" }
    if ($Raw) { return Invoke-WebRequest @args -UseBasicParsing }
    return Invoke-RestMethod @args
}

Write-Host "`n=== Multi-tenant isolation verification ===" -ForegroundColor Cyan

# --- Alice logs in ---
$alice = New-Session
$aliceMe = Invoke-Api POST "/auth/dev-login" $alice @{ username = "alice-verify" }
Check "alice dev-login returns user" ($aliceMe.username -eq "alice-verify")

$me = Invoke-Api GET "/auth/me" $alice
Check "alice /me returns alice" ($me.username -eq "alice-verify")

# --- Bob logs in (separate session) ---
$bob = New-Session
$bobMe = Invoke-Api POST "/auth/dev-login" $bob @{ username = "bob-verify" }
Check "bob dev-login returns distinct user" ($bobMe.id -ne $aliceMe.id)

# --- Alice submits a repository (POST returns the analysis job) ---
$job = Invoke-Api POST "/repositories" $alice @{ url = "https://github.com/octocat/Hello-World"; branch = "master" }
$repoId = $job.repository_id
Check "alice submit returns a job for a repo" ($null -ne $repoId)

# Fetch the repo back as alice to inspect ownership + visibility
$repo = Invoke-Api GET "/repositories/$repoId" $alice
Check "alice repo created with owner_id = alice" ($repo.owner_id -eq $aliceMe.id)
Check "alice repo defaults to private" ($repo.is_public -eq $false)

# --- Alice sees her repo in listing ---
$aliceList = Invoke-Api GET "/repositories" $alice
Check "alice listing includes her repo" ($aliceList.items.id -contains $repoId)

# --- Bob does NOT see alice's repo ---
$bobList = Invoke-Api GET "/repositories" $bob
Check "bob listing excludes alice's repo" (-not ($bobList.items.id -contains $repoId))

# --- Bob cannot GET alice's private repo (IDOR -> 404) ---
$bobGetStatus = 0
try { Invoke-Api GET "/repositories/$repoId" $bob | Out-Null }
catch { $bobGetStatus = [int]$_.Exception.Response.StatusCode }
Check "bob GET private repo -> 404 (IDOR-safe)" ($bobGetStatus -eq 404)

# --- Bob cannot access a sub-resource of alice's private repo (404) ---
$bobSubStatus = 0
try { Invoke-Api GET "/repositories/$repoId/complexity" $bob | Out-Null }
catch { $bobSubStatus = [int]$_.Exception.Response.StatusCode }
Check "bob GET private sub-resource -> 404" ($bobSubStatus -eq 404)

# --- Anonymous cannot GET alice's private repo (404) ---
$anon = New-Session
$anonGetStatus = 0
try { Invoke-Api GET "/repositories/$repoId" $anon | Out-Null }
catch { $anonGetStatus = [int]$_.Exception.Response.StatusCode }
Check "anonymous GET private repo -> 404" ($anonGetStatus -eq 404)

# --- Anonymous cannot list repos (401) ---
$anonListStatus = 0
try { Invoke-Api GET "/repositories" $anon | Out-Null }
catch { $anonListStatus = [int]$_.Exception.Response.StatusCode }
Check "anonymous listing -> 401" ($anonListStatus -eq 401)

# --- Alice makes the repo public ---
$updated = Invoke-Api PATCH "/repositories/$repoId/visibility" $alice @{ is_public = $true }
Check "alice can toggle repo public" ($updated.is_public -eq $true)

# --- Anonymous CAN now GET the public repo (200) ---
$anonPublic = Invoke-Api GET "/repositories/$repoId" $anon
Check "anonymous GET public repo -> 200" ($anonPublic.id -eq $repoId)

# --- Bob (authenticated non-owner) CAN GET the public repo ---
$bobPublic = Invoke-Api GET "/repositories/$repoId" $bob
Check "bob GET public repo -> 200" ($bobPublic.id -eq $repoId)

# --- Bob (non-owner) CANNOT mutate alice's public repo visibility (403 or 404) ---
$bobPatchStatus = 0
try { Invoke-Api PATCH "/repositories/$repoId/visibility" $bob @{ is_public = $false } | Out-Null }
catch { $bobPatchStatus = [int]$_.Exception.Response.StatusCode }
Check "bob PATCH alice's repo -> 403/404" ($bobPatchStatus -eq 403 -or $bobPatchStatus -eq 404)

# --- Bob (non-owner) CANNOT delete alice's public repo ---
$bobDeleteStatus = 0
try { Invoke-Api DELETE "/repositories/$repoId" $bob | Out-Null }
catch { $bobDeleteStatus = [int]$_.Exception.Response.StatusCode }
Check "bob DELETE alice's repo -> 403/404" ($bobDeleteStatus -eq 403 -or $bobDeleteStatus -eq 404)

# --- Alice can delete her own repo ---
$aliceDelete = Invoke-Api DELETE "/repositories/$repoId" $alice -Raw
Check "alice DELETE her own repo -> 2xx" ($aliceDelete.StatusCode -ge 200 -and $aliceDelete.StatusCode -lt 300)

# --- Logout clears the session ---
Invoke-Api POST "/auth/logout" $alice -Raw | Out-Null
$afterLogoutStatus = 0
try { Invoke-Api GET "/auth/me" $alice | Out-Null }
catch { $afterLogoutStatus = [int]$_.Exception.Response.StatusCode }
Check "after logout /me -> 401" ($afterLogoutStatus -eq 401)

Write-Host "`n=== Results: $pass passed, $fail failed ===" -ForegroundColor Cyan
if ($fail -gt 0) { exit 1 }
