# Health data access feasibility: speaker script

About 45–60 seconds.

This data path is technically feasible. Oura and WHOOP already offer official APIs: once the user signs in and grants access, our software can read the approved data. Apple Watch connects through HealthKit on the iPhone, which needs an iOS app as the entry point.

That means we can reuse devices users already own instead of building new hardware.

For this hackathon, though, we use synthetic data only: we simulate the permissions and data flow, connect no real accounts, and use no real personal or health information. The demo shows the product experience; real device integration and health effects still need to be validated.

## Sources

- Oura: https://support.ouraring.com/hc/en-us/articles/4415266939155-The-Oura-API
- Apple Watch: https://developer.apple.com/documentation/Xcode/configuring-healthkit-access
- WHOOP: https://developer.whoop.com/api/
