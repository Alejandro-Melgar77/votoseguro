[CmdletBinding()]
param(
    [ValidateSet('Plan', 'Infrastructure', 'Release')][string]$Phase = 'Plan',
    [string]$Tag = '',
    [string]$AwsProfile = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$infra = Join-Path $root 'infra/aws'
if ($AwsProfile) { $env:AWS_PROFILE = $AwsProfile }
$env:AWS_PAGER = ''

function Invoke-Tool {
    param([string]$Tool, [string[]]$Arguments)
    & rtk proxy $Tool @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Tool terminó con código $LASTEXITCODE." }
}

Push-Location $root
try {
    if (!(Test-Path (Join-Path $infra 'terraform.tfvars'))) {
        throw 'Copie infra/aws/terraform.tfvars.example a terraform.tfvars y complete dominio, certificado y correo.'
    }
    Invoke-Tool terraform @('-chdir=infra/aws', 'init', '-input=false') | Out-Host
    Invoke-Tool terraform @('-chdir=infra/aws', 'validate') | Out-Host
    if ($Phase -eq 'Plan') {
        Invoke-Tool terraform @('-chdir=infra/aws', 'plan', '-input=false') | Out-Host
        return
    }
    if ($Phase -eq 'Infrastructure') {
        # Terraform presenta el plan y solicita confirmación antes de crear recursos facturables.
        Invoke-Tool terraform @('-chdir=infra/aws', 'apply', '-var=service_enabled=false') | Out-Host
        return
    }
    if ($Tag -notmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$') {
        throw 'Indique -Tag con una etiqueta nueva e inmutable, por ejemplo un SHA de commit.'
    }
    $outputs = (Invoke-Tool terraform @('-chdir=infra/aws', 'output', '-json')) | ConvertFrom-Json
    $region = $outputs.region.value
    $repository = $outputs.ecr_repository.value
    $registry = $repository.Split('/')[0]
    $image = "${repository}:$Tag"

    Invoke-Tool aws @('ecr', 'get-login-password', '--region', $region) |
        & rtk proxy docker login --username AWS --password-stdin $registry | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo autenticar Docker en ECR.' }
    Invoke-Tool docker @('build', '--platform', 'linux/amd64', '-t', $image, 'apps/api') | Out-Host
    Invoke-Tool docker @('push', $image) | Out-Host

    # Registrar la definición nueva sin alterar aún el servicio activo ni su número de tareas.
    Invoke-Tool terraform @('-chdir=infra/aws', 'apply', "-var=image_tag=$Tag", '-target=aws_ecs_task_definition.api', '-target=aws_ecs_task_definition.scheduler') | Out-Host
    $outputs = (Invoke-Tool terraform @('-chdir=infra/aws', 'output', '-json')) | ConvertFrom-Json
    $temp = Join-Path ([IO.Path]::GetTempPath()) ('votoseguro-release-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $temp | Out-Null
    $networkFile = Join-Path $temp 'network.json'
    $overrideFile = Join-Path $temp 'overrides.json'
    [IO.File]::WriteAllText($networkFile, ($outputs.migration_network.value | ConvertTo-Json -Depth 8 -Compress))
    [IO.File]::WriteAllText($overrideFile, (@{containerOverrides=@(@{name='api';command=@('alembic','upgrade','head')})} | ConvertTo-Json -Depth 8 -Compress))
    $migration = (Invoke-Tool aws @('ecs','run-task','--region',$region,'--cluster',$outputs.cluster.value,
        '--task-definition',$outputs.api_task_definition.value,'--launch-type','FARGATE','--platform-version','1.4.0',
        '--network-configuration',"file://$networkFile",'--overrides',"file://$overrideFile",'--output','json')) | ConvertFrom-Json
    if ($migration.failures.Count -gt 0 -or !$migration.tasks[0].taskArn) { throw 'AWS no pudo iniciar la migración. Revise ECS.' }
    $taskArn = $migration.tasks[0].taskArn
    Invoke-Tool aws @('ecs','wait','tasks-stopped','--region',$region,'--cluster',$outputs.cluster.value,'--tasks',$taskArn) | Out-Host
    $status = (Invoke-Tool aws @('ecs','describe-tasks','--region',$region,'--cluster',$outputs.cluster.value,'--tasks',$taskArn,'--output','json')) | ConvertFrom-Json
    $container = $status.tasks[0].containers | Where-Object name -eq 'api'
    if ($null -eq $container.exitCode -or $container.exitCode -ne 0) {
        throw "La migración falló. Consulte CloudWatch: $taskArn. Los servicios no se actualizaron."
    }

    Invoke-Tool terraform @('-chdir=infra/aws','apply',"-var=image_tag=$Tag",'-var=service_enabled=true') | Out-Host
    Invoke-Tool aws @('ecs','wait','services-stable','--region',$region,'--cluster',$outputs.cluster.value,'--services','api','scheduler') | Out-Host
    # El waiter también puede completar tras rollback: comprobar la revisión realmente desplegada.
    $services = (Invoke-Tool aws @('ecs','describe-services','--region',$region,'--cluster',$outputs.cluster.value,'--services','api','--output','json')) | ConvertFrom-Json
    if ($services.services[0].taskDefinition -ne $outputs.api_task_definition.value) { throw 'ECS volvió a la versión anterior; consulte los eventos del servicio.' }
    $health = Invoke-RestMethod -Uri ($outputs.api_url.value + '/health')
    if ($health.database -ne 'healthy') { throw 'La API no confirmó la salud de la base.' }
    $previousApi = $env:VITE_API_BASE_URL
    try {
        $env:VITE_API_BASE_URL = $outputs.api_url.value
        Invoke-Tool pnpm @('install','--frozen-lockfile') | Out-Host
        Invoke-Tool pnpm @('--filter','@votoseguro/web','build') | Out-Host
    } finally { $env:VITE_API_BASE_URL = $previousApi }
    Invoke-Tool aws @('s3','sync','apps/web/dist',"s3://$($outputs.frontend_bucket.value)",'--region',$region,'--cache-control','public,max-age=3600','--exclude','index.html') | Out-Host
    Invoke-Tool aws @('s3','cp','apps/web/dist/index.html',"s3://$($outputs.frontend_bucket.value)/index.html",'--region',$region,'--cache-control','no-cache','--content-type','text/html') | Out-Host
    Invoke-Tool aws @('cloudfront','create-invalidation','--distribution-id',$outputs.cloudfront_id.value,'--paths','/*') | Out-Host
    Write-Host "Publicado: $($outputs.frontend_url.value)"
    Write-Host "Conserve en terraform.tfvars: image_tag = `"$Tag`" y service_enabled = true antes del siguiente plan."
} finally { Pop-Location }
