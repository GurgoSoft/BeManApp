# Script para agregar gettext al PATH del usuario
# Ejecutar como: .\setup_gettext.ps1

$gettextPath = "C:\gettext\bin"

# Obtener el PATH actual del usuario
$userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)

# Verificar si ya existe en el PATH
if ($userPath -notlike "*$gettextPath*") {
    # Agregar al PATH del usuario
    $newPath = $userPath + ";$gettextPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)
    Write-Host "Gettext agregado al PATH del usuario exitosamente" -ForegroundColor Green
    Write-Host "Debes cerrar y reabrir PowerShell para que los cambios tengan efecto" -ForegroundColor Yellow
} else {
    Write-Host "Gettext ya esta en el PATH" -ForegroundColor Green
}

# Agregar al PATH de la sesion actual tambien
$env:Path += ";$gettextPath"
Write-Host "Gettext agregado a la sesion actual de PowerShell" -ForegroundColor Green
