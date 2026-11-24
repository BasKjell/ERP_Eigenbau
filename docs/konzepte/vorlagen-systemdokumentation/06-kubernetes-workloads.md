# V06 Kubernetes-Workloads

Vorlagen-ID V06 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Anwendungen auf einer Kubernetes-Plattform (Systemtyp D). Für den Cluster selbst (Typ F) gilt dieselbe Gliederung auf Cluster-Ebene: Knoten, Steuerungsebene, Ingress, Richtlinien, Speicher. |
| Ausfüllen | Anwendungsteam mit dem Plattformteam |
| Prüfen | Plattformteam und ISB |
| Zeitpunkt | Bei Einrichtung des Namespace; Aktualisierung bei jeder Änderung an Manifesten, Richtlinien oder Rechten |
| Normbezug | APP.4.4, SYS.1.6; ISO/IEC 27001:2022 Anhang A 8.9, 8.22, 8.31, 8.32 |

[HINWEIS: Images werden in V05 Teil A dokumentiert. Ports, Ingress-Hostnamen und Zertifikate zusätzlich in V03.]

## Schritt 1: Einordnung

| Feld | Eintrag |
| --- | --- |
| Cluster und Plattformdokumentation | {{Cluster-Name}}, {{Dokument-ID der Plattform}} |
| Namespace(s) | {{Namespace}} |
| Auslieferung | {{GitOps-Repository, Pfad, Name der Argo-CD-Application oder Gleichwertiges}} |
| Pod Security Standard des Namespace | {{Auswahl: restricted; baseline; privileged (nur mit Begründung)}} |
| Ressourcenquote des Namespace | {{CPU, Arbeitsspeicher, Speicher}} |

## Schritt 2: Workloads

| Name | Art | Images (siehe V05) | Replikate | Requests und Limits | Probes | Unterbrechungsbudget |
| --- | --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: Deployment; StatefulSet; DaemonSet; Job; CronJob}} | {{Image@Digest}} | {{Anzahl}} | {{Werte}} | {{liveness, readiness}} | {{PodDisruptionBudget}} |

## Schritt 3: Sicherheitskontext

| Workload | runAsNonRoot | readOnlyRootFilesystem | allowPrivilegeEscalation | Capabilities | seccompProfile | hostNetwork, hostPID, hostPath | ServiceAccount | Token eingebunden |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {{Name}} | {{true/false}} | {{true/false}} | {{false}} | {{drop ALL, add …}} | {{RuntimeDefault}} | {{müssen „nein“ sein oder begründet}} | {{Name}} | {{ja/nein}} |

## Schritt 4: Netz

Services und Zugang von außen:

| Service bzw. Ingress | Typ | Host und Pfad | Port | TLS |
| --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: ClusterIP; LoadBalancer; Ingress; Gateway-Route}} | {{Host}} | {{Port}} | {{Zertifikat, siehe V03}} |

Netzwerkregeln (NetworkPolicy):

| Regel | Von | Nach | Port | Zweck |
| --- | --- | --- | --- | --- |
| {{Name}} | {{Quelle}} | {{Ziel}} | {{Port}} | {{Zweck}} |

[HINWEIS: Grundsatz ist eine Regel „alles sperren“ für ein- und ausgehenden Verkehr im Namespace und darauf aufbauende Freigaben. DNS-Auflösung muss ausdrücklich erlaubt werden.]

## Schritt 5: Identität und Rechte (RBAC)

| Subjekt | Art | Rolle bzw. ClusterRole | Rechte (Verben, Ressourcen) | Begründung |
| --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: ServiceAccount; Gruppe aus dem Identitätsdienst}} | {{Rolle}} | {{Verben, Ressourcen}} | {{Begründung}} |

## Schritt 6: Konfiguration und Geheimnisse

| Objekt | Art | Quelle | Inhalt |
| --- | --- | --- | --- |
| {{Name}} | {{Auswahl: ConfigMap; Secret}} | {{Auswahl: Git; Secret-Manager über External Secrets; verschlüsselt im Git}} | {{Beschreibung, keine Werte}} |

## Schritt 7: Speicher

| PersistentVolumeClaim | StorageClass | Größe | Zugriffsart | Inhalt | Sicherung (siehe V10) |
| --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Klasse}} | {{GB}} | {{RWO/RWX}} | {{Inhalt}} | {{Verfahren}} |

## Schritt 8: Richtlinien und Ausnahmen

| Richtlinie | Wirkung | Ausnahme für diesen Namespace | Begründung | Befristet bis |
| --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: erzwingen; prüfen}} | {{ja/nein}} | {{Begründung}} | {{Datum}} |

## Schritt 9: Auslieferung und Rücknahme

| Feld | Eintrag |
| --- | --- |
| Weg einer Änderung | {{Merge Request → Prüfung → Synchronisation}} |
| Rücknahme | {{zum Beispiel Revert im Git, Synchronisation}} |
| Wer darf synchronisieren | {{Rolle}} |

## Ist-Stand erheben

| Zweck | Befehl |
| --- | --- |
| Alle Objekte im Namespace | `kubectl get all -n <ns>` |
| Netz, Speicher, Rechte | `kubectl get networkpolicy,ingress,pvc,serviceaccount,rolebinding -n <ns>` |
| Pod Security Standard | `kubectl get ns <ns> --show-labels` |
| Rechte eines ServiceAccounts | `kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa> -n <ns>` |
| Wirksame Manifeste | `kubectl get deploy,statefulset -n <ns> -o yaml` |

## Prüfpunkte

- ☐ Namespace läuft mindestens mit Pod Security Standard „baseline“, Ziel „restricted“.
- ☐ Kein Workload nutzt hostNetwork, hostPID oder hostPath ohne genehmigte Begründung.
- ☐ Eine Regel „alles sperren“ ist aktiv; jede Freigabe steht in Schritt 4.
- ☐ ServiceAccounts haben nur die nötigen Rechte; Token werden nur eingebunden, wo nötig.
- ☐ Keine Geheimnisse im Klartext im Git.
- ☐ Alle Manifeste kommen aus Git; manuelle Änderungen im Cluster sind ausgeschlossen bzw. werden überschrieben.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-06] Plattformteam und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Zuordnung von Anwendungen zu Clustern nach Schutzbedarf | offen | Plattformteam |
| Mindest-Pod-Security-Standard | offen | ISB |
| Pflicht zur Regel „alles sperren“ in jedem Namespace | offen | ISB |
| Richtlinien-Werkzeug und verbindliche Regeln | offen | Plattformteam |
| Standardquoten je Namespace | offen | Plattformteam |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    Das durchgängige Beispiel SYS-0042 läuft auf Docker Compose. Zur Veranschaulichung zeigt dieses Beispiel, wie dieselbe Anwendung auf der Kubernetes-Plattform dokumentiert würde.

    | Feld | Eintrag |
    | --- | --- |
    | Cluster | k8s-prod-01, Plattformdokumentation PLT-0007 |
    | Namespace | flowdoc |
    | Auslieferung | Repository gitops/apps, Pfad flowdoc/prod, Argo-CD-Application flowdoc-prod |
    | Pod Security Standard | restricted |
    | Quote | 6 CPU, 12 GB RAM, 600 GB Speicher |

    | Name | Art | Image | Replikate | Requests/Limits | Probes | Budget |
    | --- | --- | --- | --- | --- | --- | --- |
    | flowdoc-web | Deployment | paperless-ngx@sha256:3f9a… | 2 | 1/2 CPU, 2/4 GB | liveness und readiness auf /api/ | minAvailable 1 |
    | flowdoc-db | Cluster der Datenbank über CloudNativePG | postgres@sha256:91c2… | 2 | 1/2 CPU, 2/4 GB | durch Operator | durch Operator |

    | Workload | runAsNonRoot | readOnlyRootFilesystem | allowPrivilegeEscalation | Capabilities | seccomp | host… | ServiceAccount | Token |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | flowdoc-web | true (UID 1000) | false, beschreibbar nur /data und /media | false | drop ALL | RuntimeDefault | nein | flowdoc-web | nein |

    | Service bzw. Ingress | Typ | Host | Port | TLS |
    | --- | --- | --- | --- | --- |
    | flowdoc | Ingress | flowdoc.flowcorp.example / | 443 | Zertifikat über cert-manager |

    | Regel | Von | Nach | Port | Zweck |
    | --- | --- | --- | --- | --- |
    | default-deny | alle | alle | alle | Grundregel |
    | allow-ingress | Namespace ingress | flowdoc-web | 8000 | Weboberfläche |
    | allow-db | flowdoc-web | flowdoc-db | 5432 | Datenbank |
    | allow-dns | flowdoc | kube-dns | 53 | Namensauflösung |
    | allow-imap | flowdoc-web | mail.flowcorp.example | 993 | Belegabruf |

    RBAC: ServiceAccount flowdoc-web ohne Rechte an der Kubernetes-API; Gruppe GG-K8S-FLOWDOC-BETRIEB mit der ClusterRole „view“, gebunden nur an den Namespace flowdoc; Befehle in Pods per exec nur über eine befristete Notfallrolle mit Freigabe.

    Geheimnisse: flowdoc-db-app, flowdoc-oidc, flowdoc-imap über External Secrets aus dem Secret-Manager; keine Werte im Git.

    Speicher: flowdoc-media 500 GB, StorageClass ceph-rbd, RWO, gesichert mit Velero täglich; Datenbank über Sicherung des Operators.

    Richtlinien: alle Regeln der Plattform erzwungen, keine Ausnahme.
