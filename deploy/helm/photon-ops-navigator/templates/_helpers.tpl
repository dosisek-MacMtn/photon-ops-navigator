{{- define "photonops.name" -}}photon-ops-navigator{{- end -}}
{{- define "photonops.fullname" -}}{{ .Release.Name }}{{- end -}}
{{- define "photonops.labels" -}}
app.kubernetes.io/name: {{ include "photonops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
{{- define "photonops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}{{ default (include "photonops.fullname" .) .Values.serviceAccount.name }}{{ else }}{{ .Values.serviceAccount.name }}{{ end }}
{{- end -}}
