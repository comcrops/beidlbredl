# Overview - beidlbredl

- Modular dashboard web app
- Apps for different purposes
    - Dave Counter
    - Weather
    - Drink/tütn counter
    - music controls
    - caravento menu (mittag.at api)
    - metriken zur anwesenheit über WLAN connection
- Easily extendable
- Language Upper-Austrian ask for clarifying stuff
- Mobile Controls
    - Genereal Purpose
        - Right, left switching apps
        - Home, etc
    - App specific
        - Apps can specify custom controls
    - websocket, multi user
- Runs in Kiosk Mode on Browser
    - Runs in one instance that displays the dashboard
- LDAP Accounts / OIDC connection (authentik in backend)
    - WPA3 with auth portal for wifi
- Apps are subpages
    - cycle apps on dashboard carousel



## Tech Stack
- Everything runs on one Raspberry Pi with monitor
    - Authentik is external
- Authentik for user management
- Pocket Base for Dashboard and App specific data storage
- Flask for backend
- Some sort of SPA frontend
    - use flask for both?
    - use something different?
