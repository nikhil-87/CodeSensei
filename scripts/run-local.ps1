param(
    [ValidateSet('all', 'infra', 'backend', 'worker', 'frontend', 'down', 'ps', 'logs', 'health')]
    [string]$Action = 'all',
    [ValidateSet('backend', 'worker', 'frontend', 'postgres', 'redis', 'chroma', 'ollama')]
    [string]$Service = 'backend'
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

$docker = (Get-Command docker.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $docker) {
    $docker = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
}

if (-not (Test-Path $docker)) {
    throw 'Docker CLI not found. Install Docker Desktop or add docker.exe to PATH.'
}

$envFileLocal = Join-Path $repoRoot '.env.local'
$envFile = if (Test-Path $envFileLocal) { $envFileLocal } else { Join-Path $repoRoot '.env' }

$composeArgs = @('-f', 'docker/docker-compose.yml', '--env-file', $envFile)

function Invoke-Compose {
    param([string[]]$Arguments)
    & $docker compose @composeArgs @Arguments
}

switch ($Action) {
    'infra' {
        Invoke-Compose -Arguments @('up', '-d', '--build', 'postgres', 'redis', 'chroma', 'ollama')
    }
    'backend' {
        Invoke-Compose -Arguments @('up', '-d', '--build', 'backend')
    }
    'worker' {
        Invoke-Compose -Arguments @('up', '-d', '--build', 'worker')
    }
    'frontend' {
        Invoke-Compose -Arguments @('up', '-d', '--build', 'frontend')
    }
    'all' {
        Invoke-Compose -Arguments @('up', '-d', '--build', 'postgres', 'redis', 'chroma', 'ollama', 'backend', 'worker', 'frontend')
    }
    'down' {
        Invoke-Compose -Arguments @('down')
    }
    'ps' {
        Invoke-Compose -Arguments @('ps')
    }
    'logs' {
        Invoke-Compose -Arguments @('logs', '-f', '--tail=100', $Service)
    }
    'health' {
        $checks = @(
            @{ Name = 'backend'; Url = 'http://localhost:8001/healthz' },
            @{ Name = 'frontend'; Url = 'http://localhost:5173/healthz' }
        )

        foreach ($check in $checks) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing $check.Url
                Write-Host "$($check.Name): $($response.StatusCode) $($response.Content)"
            }
            catch {
                Write-Host "$($check.Name): FAILED ($($_.Exception.Message))"
                exit 1
            }
        }
    }
}