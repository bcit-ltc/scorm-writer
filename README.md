# Scorm-writer

`scorm-writer` is a question converter that enables accurate text conversion from Word into an LMS import package. It requires the frontend, `qcon-web` to work correctly. Together, these apps form the [`Qcon` service](https://qcon.ltc.bcit.ca).

## Quick Start

    docker run -p 8000:8000 ghcr.io/bcit-ltc/scorm-writer

Open your browser to [http://localhost:8000](http://localhost:8000).

## Using `scorm-writer`

See [Qcon Usage and Examples](https://qcon-guide.ltc.bcit.ca) for documentation about the Qcon service, including what to do after the conversion to get your questions into your LMS.

## Development

    docker compose up --build

## Support

If you need any help with `qcon`, please see the [Qcon Guide](https://qcon-guide.ltc.bcit.ca) or [contact us](mailto:ltc_techops@bcit.ca).

Please submit any `scorm-writer` bugs, issues, and feature requests to the [bcit-ltc/scorm-writer](https://github.com/bcit-ltc/scorm-writer) source code repo.

## License

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at [https://mozilla.org/MPL/2.0/](https://mozilla.org/MPL/2.0/).
