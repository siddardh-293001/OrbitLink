# ORBITLINK architecture

```mermaid
flowchart TD
  C[Core models and configuration] --> O[Orbit propagation]
  O --> G[Geometry and visibility]
  G --> R[RF and optical communication]
  R --> M[Satellite selection and handover]
  R --> N[Dynamic topology, routing and packet queues]
  M --> A[Analytics and experiments]
  N --> A
  A --> V[2D, 3D and network visualization]
  V --> D[Streamlit dashboard]
```

The engine layers remain independent of Streamlit so batch runs, tests and the dashboard use the same physics and network logic. Configuration and assumed link parameters are kept visible to experiments.
