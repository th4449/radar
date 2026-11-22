# Tesseract, for reading scanned PDFs

- Used by: `pipeline/ocr.py`, called from `pipeline/extract.py` for a PDF with no text in it
- What it is: a free program that reads the words in a picture of a page
- Project: https://github.com/tesseract-ocr/tesseract
- License: Apache 2.0, for the program and for its English language data. Read from each project's license file on November 21, 2026.
- Checked: November 21, 2026
- Result: **used, on our own machines only.** Nothing is sent to any service.

The owner said on November 21, 2026 to build this. The first run of the own-sites agenda collector stored 43 agenda files and 28 of them were scans the radar could not read.

## What it does here

- A PDF with a text layer is read as before. It never goes to Tesseract.
- **A PDF with no text at all** is drawn page by page as a picture at 300 dots an inch, and each picture is given to Tesseract.
- The scan itself is what is stored. The text is a machine's reading of it.
- **Everything read this way is marked.** The stored document carries the engine and its version, the number of pages read, the number of words, Tesseract's mean score for them and how many it doubted. A signal made from that text says in its summary that the file is a scan read by character recognition.
- At most 150 pages of one file are read. A longer scan is a packet, and its first pages hold the agenda.
- **Where Tesseract is not installed, nothing fails.** A scan is stored unread and counted as unread, as before.

It is a program, not a Python package. CI and the collect workflow install it with `apt-get`. On a Mac: `brew install tesseract`.

## Measured on real agendas

On November 21, 2026, with Tesseract 5.5.4, on the 43 agenda files the first own-sites run stored. The files stayed on this machine.

**The 28 scans**

- **All 28 gave text.** 27 of them show the word "agenda". The other is a notice that a meeting was cancelled.
- 233 pages took 203 seconds, under a second a page.
- Tesseract's own mean score for a file ran from 73 to 96 out of 100. The middle file scored 95.
- **Two more signals.** Merkel's council agenda for November 17, 2026 has two items on a tax increment reinvestment zone. A 125-page packet uses the words "development agreement" on pages 61 and 65.
- **Checked by eye:** the first page of Merkel's agenda against its picture, and the first page of the lowest-scoring file. Running text was right in both. I found one stray character.

**The 13 files that have their own text,** read both ways, to check OCR against the truth

- **9,762 of 9,771 words of three letters or more came out the same:** 99.9 percent.
- Both keyword matches in the text were found by OCR. OCR found none that were not there.
- This is the best case. A page drawn from a clean file is sharper than paper put through a scanner.

## What it does badly

- **Tables come out jumbled.** In the lowest-scoring file, a table of parcels and owners lost its columns. The sentences above it read correctly.
- A stamp, a seal or a signature becomes a few stray characters.

## What was not verified

- **Accuracy on real scans as a number.** There is no typed copy of a scan to check against. Two pages were checked by eye.
- **Whether a keyword in a scan is ever missed.** A misread letter in "data center" would lose the match. The clean-file test missed none of two.
- Pages scanned sideways or upside down. Tesseract is run without its orientation step.
- Handwriting, and any language but English.
- **A file that is part text and part scan.** Only a file with no text at all is read by OCR, so a typed agenda with scanned attachments is read for its typed pages only.
- A scan embedded inside another PDF or held in a zip file. Those are not read by OCR.
- **Whether GitHub's runners read a real scan as this machine does.** The runner installs Tesseract 5.5.0 with Ubuntu's English data package 4.1.0. This machine has 5.5.4 from Homebrew, and the 28 scans were measured here only. All tests pass on the runner (CI run 44969618367, November 21, 2026). They ask for the words on a made-up typed page and not for an exact reading.
- **A scan the text reader finds no pages in.** One real county agenda was such a file. It is now counted by the page drawer and read. Fixed November 22, 2026. No file of the first 43 was of this kind.
- Scans stored before this was built. There are none in a database yet. A stored scan is read when the file is next fetched or its text is extracted again.
