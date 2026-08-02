# Isolated QuantLib reference validation

This uv project uses QuantLib 1.43 only as an independent, offline test
reference for Options Validator. It is not a root or production dependency,
is not imported by scanner or dashboard code, and has no authority to change a
hypothesis, verdict, portfolio, provider, cache, ledger, or order path. It uses
no API key, hosted service, telemetry, paid feature, or market-data request.

## Run

From the repository root:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache \
  uv run --project tools/quantlib_validation --frozen \
  python -m unittest discover -s tools/quantlib_validation/tests -v
```

The lock pins `QuantLib==1.43`. After the locked wheel is available locally,
the validation run is fully offline.

## Declared conventions

- Dates use QuantLib `Actual/365 (Fixed)`.
- European options with a continuous dividend yield use
  `AnalyticEuropeanEngine`.
- American options with a continuous dividend yield use
  `FdBlackScholesVanillaEngine`.
- Discrete cash dividends use QuantLib 1.43's verified `DividendSchedule`
  overload of `FdBlackScholesVanillaEngine`; they are never approximated as a
  continuous yield. This finite-difference path supports both European and
  American exercise.
- The default finite-difference grid is 400 time steps by 200 price-grid
  points and uses QuantLib's default Douglas scheme. Individual convergence
  tests declare any alternate grids in their requests.
- Analytic reference comparisons use a `1e-10` price tolerance. American
  dominance checks allow `1e-8` for numerical noise, and the refined
  non-dividend American-call convergence check uses a `0.01` price tolerance.
- Results contain only Python primitives, enums, dates, and frozen dataclasses;
  no raw QuantLib object escapes the adapter.

QuantLib's evaluation date is process-global. The adapter serializes its own
calls with one lock and restores the previous date in `finally`, including
when native pricing raises. This is not a general thread-safety guarantee:
uncoordinated QuantLib use elsewhere in the same process can still race. Run
this validation as the isolated single-process command above.

Invalid dates, non-finite or nonpositive market inputs, mixed dividend models,
malformed dividend schedules, and invalid grids fail before native pricing.
Native failures are re-raised with engine/style context and preserve the
original exception as their cause.

## Rollback

Revert the standalone `feat(options): add isolated QuantLib validation` commit.
That removes this directory and its CI step without changing production
pricing or any research artifact.

## License and required notice

QuantLib 1.43 is free and open source under the BSD 3-Clause license. The
official wheel retains the same notice at
`share/doc/quantlib/LICENSE.TXT`. Redistribution of the wheel must retain the
following copyright, conditions, and disclaimer in documentation or other
distributed materials.

```text
Copyright (C) 2000, 2001, 2002, 2003 RiskMap srl
Copyright (C) 2002, 2003 Ferdinando Ametrano
Copyright (C) 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2014, 2020, 2022, 2023 StatPro Italia srl
Copyright (C) 2005 Dominic Thuillier
Copyright (C) 2005 Johan Witters
Copyright (C) 2007 Eric H. Jensen
Copyright (C) 2007 Luis Cota
Copyright (C) 2007 Richard Gomes
Copyright (C) 2007, 2008 Tito Ingargiola
Copyright (C) 2007, 2010 Joseph Wang
Copyright (C) 2008 Allen Kuo
Copyright (C) 2008 Florent Grenier
Copyright (C) 2009 Joseph Malicki
Copyright (C) 2010 Andrea Odetti
Copyright (C) 2010, 2011 Lluis Pujol Bajador
Copyright (C) 2010, 2011, 2012, 2013, 2014, 2015, 2018, 2019, 2020, 2021, 2022, 2023, 2024 Klaus Spanderen
Copyright (C) 2011, 2012 Tawanda Gwena
Copyright (C) 2012 Francis Duffy
Copyright (C) 2013 Simon Shakeshaft
Copyright (C) 2014 Bitquant Research Laboratories (Asia) Ltd.
Copyright (C) 2014 Simon Mazzucca
Copyright (C) 2014 Wondersys Srl
Copyright (C) 2014, 2015 Thema Consulting SA
Copyright (C) 2014, 2015, 2018 Matthias Groncki
Copyright (C) 2015, 2016 Gouthaman Balaraman
Copyright (C) 2016 Peter Caspers
Copyright (C) 2016, 2017, 2018, 2019 Wojciech Ślusarski
Copyright (C) 2017 BN Algorithms Ltd
Copyright (C) 2017, 2018, 2019, 2020 Matthias Lungwitz
Copyright (C) 2018 Angus Lee
Copyright (C) 2019 Pedro Coelho
Copyright (C) 2019 Prasad Somwanshi
Copyright (C) 2020 Gorazd Brumen
Copyright (C) 2020, 2021, 2022 Jack Gillett
Copyright (C) 2020, 2021, 2023 Marcin Rybacki
Copyright (C) 2021, 2024 Ralf Konrad Eckel
Copyright (C) 2022 Ignacio Anguita
Copyright (C) 2022, 2023, 2024 Skandinaviska Enskilda Banken AB (publ)
Copyright (C) 2023 Francois Botha
Copyright (C) 2025 Hiroto Ogawa
Copyright (C) 2026 Arihant Lodha

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the names of the copyright holders nor the names of the QuantLib
   Group and its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
