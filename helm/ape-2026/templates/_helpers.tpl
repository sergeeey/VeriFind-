{{/*
Expand the name of the chart.
*/}}
{{- define "ape-2026.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ape-2026.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ape-2026.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ape-2026.labels" -}}
helm.sh/chart: {{ include "ape-2026.chart" . }}
{{ include "ape-2026.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ape-2026.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ape-2026.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ape-2026.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ape-2026.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "ape-2026.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "ape-2026.fullname" .) }}
{{- else }}
{{- .Values.configMaps.api.POSTGRES_HOST }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "ape-2026.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "ape-2026.fullname" .) }}
{{- else }}
{{- .Values.configMaps.api.REDIS_HOST }}
{{- end }}
{{- end }}

{{/*
Neo4j URI
*/}}
{{- define "ape-2026.neo4j.uri" -}}
{{- if .Values.neo4j.enabled }}
{{- printf "bolt://%s-neo4j:7687" (include "ape-2026.fullname" .) }}
{{- else }}
{{- .Values.configMaps.api.NEO4J_URI }}
{{- end }}
{{- end }}
