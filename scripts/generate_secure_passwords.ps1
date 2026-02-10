#!/usr/bin/env pwsh
# Generate secure passwords for APE 2026
# Usage: .\scripts\generate_secure_passwords.ps1

function Get-RandomPassword {
    param(
        [int]$Length = 32
    )
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    $password = -join ((1..$Length) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    return $password
}

function Get-RandomHex {
    param(
        [int]$Length = 64
    )
    $bytes = New-Object byte[] ($Length / 2)
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([BitConverter]::ToString($bytes) -replace '-', '').ToLower()
}

Write-Host "# Generated secure passwords for APE 2026" -ForegroundColor Green
Write-Host "# Copy these values to your .env file" -ForegroundColor Yellow
Write-Host ""

Write-Host "NEO4J_PASSWORD=$(Get-RandomPassword -Length 32)"
Write-Host "POSTGRES_PASSWORD=$(Get-RandomPassword -Length 32)"
Write-Host "SECRET_KEY=$(Get-RandomHex -Length 128)"
Write-Host "GRAFANA_ADMIN_PASSWORD=$(Get-RandomPassword -Length 32)"

Write-Host ""
Write-Host "# IMPORTANT: Keep your API keys unchanged!" -ForegroundColor Cyan
Write-Host "# DEEPSEEK_API_KEY=sk-... (keep existing)" -ForegroundColor Gray
Write-Host "# ANTHROPIC_API_KEY=sk-... (keep existing)" -ForegroundColor Gray
Write-Host "# OPENAI_API_KEY=sk-... (keep existing)" -ForegroundColor Gray
