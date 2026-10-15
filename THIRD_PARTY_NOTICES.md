# Third-party notices

Project-owned code, documentation and synthetic examples use the MIT license in `LICENSE`. Python and separately installed packages retain their own licenses. No firmware, detector implementation, Home Assistant code or private adapter is vendored here.

The core reporting engine and offline demonstration require only Python's standard library. The optional `record` extra installs **aiohttp 3.14.3**, declared `Apache-2.0 AND MIT` by its exact distribution. Preserve [aiohttp notices](LICENSES/aiohttp.txt) and the bundled [llhttp notice](LICENSES/llhttp.txt); see its installed distribution license and [upstream repository](https://github.com/aio-libs/aiohttp). Its dependencies retain their own upstream licenses. The package index and wheel metadata provide the resolved list for your installation.

Build and development tools include setuptools, build, pytest and Ruff; they are not shipped as project source and retain their own licenses. Use dependency inspection appropriate to your distribution when redistributing a full Python environment.

Home Assistant and RuView names describe interoperability. This project is not an official integration or an endorsement by either project.

## Shared release tooling

Generated release and workflow-contract helpers are from [venus-os-ci-toolkit](https://github.com/victron-venus/venus-os-ci-toolkit), pinned by `.release-policy.json`. The following license applies to those files.

MIT License

Copyright (c) 2026 victron-venus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
