$files = @(
    "api/v1/__init__.py",
    "api/v1/audit_logs.py",
    "api/v1/auth.py",
    "api/v1/backups.py",
    "api/v1/categories.py",
    "api/v1/drones.py",
    "api/v1/invoices.py",
    "api/v1/materials.py",
    "api/v1/news.py",
    "api/v1/orders.py",
    "api/v1/roles.py",
    "api/v1/user_addresses.py",
    "api/v1/users.py",
    "api/v1/warehouse_documents.py",
    "api/v1/warehouses.py",
    "api/__init__.py",
    "api/deps.py",
    "core/config.py",
    "core/database.py",
    "core/exceptions.py",
    "core/file_validation.py",
    "core/logger.py",
    "core/permissions.py",
    "core/rate_limit.py",
    "core/security.py",
    "core/security_headers.py",
    "models/__init__.py",
    "models/audit_log.py",
    "models/category.py",
    "models/drone.py",
    "models/invoice.py",
    "models/material.py",
    "models/news.py",
    "models/order.py",
    "models/role.py",
    "models/user.py",
    "models/warehouse.py",
    "private/backups/.gitkeep",
    "schemas/__init__.py",
    "schemas/audit_log.py",
    "schemas/category.py",
    "schemas/drone.py",
    "schemas/invoice.py",
    "schemas/material.py",
    "schemas/news.py",
    "schemas/order.py",
    "schemas/role.py",
    "schemas/token.py",
    "schemas/user.py",
    "schemas/warehouse.py",
    "schemas/warehouse_document.py",
    "services/backup_service.py",
    "services/feasibility_service.py",
    "services/invoice_service.py",
    "services/otp_service.py",
    "services/warehouse_service.py",
    "storage/avatars/.gitkeep",
    "storage/drones/.gitkeep",
    "logs/app.log",
    "logs/audit.log",
    ".env",
    "requirements.txt",
    "tree_exporter.py"
)

foreach ($file in $files) {
    $parentDir = Split-Path -Path $file -Parent
    if ($parentDir -and -not (Test-Path -Path $parentDir)) {
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        Write-Host "Directory created: $parentDir" -ForegroundColor Cyan
    }
    if (-not (Test-Path -Path $file)) {
        New-Item -ItemType File -Path $file -Force | Out-Null
        Write-Host "File created: $file" -ForegroundColor Green
    }
}

Write-Host "`nProject structure for dronfactory_api created successfully!" -ForegroundColor Yellow