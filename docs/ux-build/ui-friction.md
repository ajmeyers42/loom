# UI build friction log (implementation → UX chat)

| Screen | What the SA needed | What the backend returns | Type |
|--------|-------------------|---------------------------|------|
| SB-01 Create | Live identity validation before submit | No CLI command; added `POST /api/validate-public` (wraps `find_identity_leaks`) | extra-step |
| SB-02 Keystore | Sibling picklist on create (no slug yet) | `keys list` requires a slug; Overview must pick/create first | contract-gap |
| SB-03 Evidence | Paste/upload notes without temp path | `inputs add` is path-based; UI writes temp with **client filename** (or `content_base64`) then CLI/bootstrap | resolved (file picker on Create + Evidence) |
| Overview | `identity.aliases[]` editing | Not in pipeline-state API surface | missing-info |
| SB-03 Evidence | Import mode “evidence unverified” banner | listen record warnings only after record | missing-info |
| All screens | Switch nav before Overview fetch finishes | Client race overwrote the active screen; fixed with view generation guard | copy |
| Embedded browser | API calls with `Origin: null` | Server now treats `Origin: null` like absent for localhost fetches | contract-gap |
