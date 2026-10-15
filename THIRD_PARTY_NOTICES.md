# Third-party notices

Project-owned code, documentation and synthetic examples use the MIT license in `LICENSE`. Python and separately installed packages retain their own licenses. No firmware, detector implementation, Home Assistant code or private adapter is vendored here.

The core reporting engine and offline demonstration require only Python's standard library. The optional `record` extra installs **aiohttp 3.13.3**, declared `Apache-2.0 AND MIT` by its exact distribution. Preserve [aiohttp notices](LICENSES/aiohttp.txt) and the bundled [llhttp notice](LICENSES/llhttp.txt); see its installed distribution license and [upstream repository](https://github.com/aio-libs/aiohttp). Its dependencies retain their own upstream licenses. The package index and wheel metadata provide the resolved list for your installation.

Build and development tools include setuptools, build, pytest and Ruff; they are not shipped as project source and retain their own licenses. Use dependency inspection appropriate to your distribution when redistributing a full Python environment.

Home Assistant and RuView names describe interoperability. This project is not an official integration or an endorsement by either project.
