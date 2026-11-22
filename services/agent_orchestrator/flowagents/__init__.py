"""FLOWAGENTS – Orchestrator für die rollengetrennte KI-Entwicklung der FLOW-Plattform.

Der Orchestrator ist ein deterministischer Dienst. Er führt den versionierten Ablauf aus
``agents/workflow.yaml`` aus, startet je Schritt genau eine Rolle aus ``agents/registry.yaml``,
prüft deren maschinenlesbare Übergabe und hält Zustand, Ereignisse und Entscheidungen dauerhaft
fest. Modelle erhalten keine Werkzeuge: Werkzeugaufrufe in FLOWWORK führt der Orchestrator mit
der rollengebundenen Identität aus, und der RM-Adapter prüft sie serverseitig erneut.
"""

__version__ = "0.1.0"
