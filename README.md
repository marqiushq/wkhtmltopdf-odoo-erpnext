# wkhtmltopdf for Odoo and ERPNext: will my reports still print if I replace wkhtmltopdf?

**Odoo and ERPNext make every PDF with wkhtmltopdf.** When someone presses Print on an invoice, a quotation or a delivery slip, the application hands the page to wkhtmltopdf and sends back the PDF it makes. wkhtmltopdf was archived in January 2023. It gets no security fixes, and it is gone from Debian 13 and Ubuntu 26.04, so new servers can no longer install it from their own package lists.

**This repository prints the standard reports of every Odoo and ERPNext version still supported, through each application's own Print button, with two programs in wkhtmltopdf's place:** the original wkhtmltopdf 0.12.6, and marqius-wkhtmltopdf, its maintained replacement. Each PDF is then compared with wkhtmltopdf's, page by page. The rule is simple: every document wkhtmltopdf prints, marqius-wkhtmltopdf must print with the same words, numbers, dates, pictures and pages.

**Why it matters.** It answers "will our invoices still come out right after we switch?" with the application's own reports, printed the way your users print them, on both kinds of server: Intel/AMD (x86-64) and ARM. Every run happens on GitHub's machines, in public, and every results file is signed by the run that made it, so nobody can quietly change a number.

> marqius-wkhtmltopdf is a paid product of Simple AI LLC, which publishes these tests. The harness is open (MIT). We publish the misses along with the matches. If a result looks wrong to you, please open an issue.

Calling wkhtmltopdf from your own code through a library such as pdfkit, wicked_pdf or laravel-snappy? [wkhtmltopdf library tests](https://github.com/marqiushq/wkhtmltopdf-library-tests) runs 15 of those libraries' own test suites with the same two programs.

## The results

**GO** means nothing worth looking at: every document printed, and `marqius-wkhtmltopdf compare` found no word, number, date, picture or page missing or changed. **REVIEW** means the content is the same and the layout differs in a way a person may want to look at. **NO-GO** means content changed or a document did not print. The time is how long the documents took through the application's Print route; in brackets, how many times faster than wkhtmltopdf.

<!-- results:start -->
The first results appear here after the first run.
<!-- results:end -->

Each result's full report, with what the application said whenever a document did not print, is under [`results/`](results/).

## What is printed

**Odoo 18.0, 19.0 and 20.0**, the three versions Odoo supports, with Odoo's demo data and these documents, made with fixed dates:
- invoices of one page and of several, three invoices at once, two companies' invoices at once, and an invoice with a missing picture;
- quotations, short and long, and three at once;
- delivery slips, alone and three at once, and a picking list.

Each Odoo version runs on two systems:
- **Odoo's own Docker image** (Ubuntu 24.04). Its wkhtmltopdf is upstream's 0.12.6.1-3 package with patched Qt, which Odoo installs there. That is the reference.
- **Debian 13**, with Odoo's own Debian package, the same build as in Odoo's image (checked file by file), installed with apt. Debian 13 has no wkhtmltopdf package, so only marqius-wkhtmltopdf runs there.

**ERPNext 15 and 16**, the two versions Frappe supports, from ERPNext's own Docker image as frappe_docker's quick start runs it:
- a company with the standard chart of accounts;
- a letterhead whose footer carries the page numbers;
- item tables narrowed to six columns (item, description, quantity, unit, rate, amount), as most companies narrow them. With every column ERPNext prints by default, they are wider than A4, and each program cuts or squeezes the overflow its own way;
- these documents, with fixed names and dates: invoices of one page and of several, three invoices at once, a quotation, a sales order, a delivery note, a purchase order, and an invoice with a missing picture.

ERPNext 15's image is Debian 12; 16's is Debian 13. Both carry upstream's wkhtmltopdf 0.12.6.1-3 package for Debian 12, which is the reference. ERPNext 16 makes PDFs with Chrome unless told otherwise, so here it is told to use wkhtmltopdf, as on 15. ERPNext 17 drops wkhtmltopdf.

**Every version runs twice:** on GitHub's x86-64 machines and on its ARM64 machines.

## How each program is installed

- **wkhtmltopdf 0.12.6**: the copy in the application's image. It is checked byte for byte against upstream's 0.12.6.1-3 package.
- **marqius-wkhtmltopdf**: its one-line installer, given the version, reading files checked against the SHA-256 sums marqius.com publishes and against the program's GitHub provenance attestation.

For marqius-wkhtmltopdf, wkhtmltopdf's package is removed first. A stand-in at `/usr/local/bin/wkhtmltopdf` passes every call to the program unchanged and records the command line, the exit status and the time.

## How the PDFs are judged

`marqius-wkhtmltopdf compare` reads each PDF the way a person reads it and compares it with the reference's: words, numbers, dates, pictures, pages, and where things stand. A difference blocks when content changes: a word, number, date or picture missing, added or different. Some findings are checked again before they count:
- **Pictures.** compare reads the colour values a PDF stores, and two programs can store the same picture differently. So every picture it calls changed is laid on white through its own transparency, as a viewer shows it, and compared pixel by pixel. It counts as changed only if it looks different.
- **Page numbers.** When a program fits the same lines on fewer or more pages, the page numbers ("Page 2 / 4") follow. That is a layout difference to look at, not changed content.
- **Moved words.** When the same words are both missing in one place and added in another in one document, a line wrapped at another word. Nothing was lost, so that is to look at too.
- **Invisible characters.** A zero-width space or a soft hyphen that one program keeps in the text shows nothing on the page, so it is not counted.

## When it runs

- at every marqius-wkhtmltopdf release, the same day;
- every Monday, with the latest Odoo and ERPNext images, so a change in either shows within a week;
- by hand.

## Check these results

Each run's files are attested by the run that made them. With the GitHub CLI, signed in:

```bash
git clone https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext.git
cd wkhtmltopdf-odoo-erpnext
gh attestation verify results/history.tsv -R marqiushq/wkhtmltopdf-odoo-erpnext
```

It shows the workflow, the commit and the run that made the file.

## Run it yourself

Fork this repository and start **Actions > Reports > Run workflow**. Or run one cell on a Linux x86-64 machine with Docker, jq and the GitHub CLI signed in (it checks the program's attestation):

```bash
mq=$(curl -fsS https://marqius.com/download/marqius-wkhtmltopdf/latest)
bash harness/programs.sh "$mq" x86-64 programs
bash harness/odoo/cell.sh 19.0 x86-64 programs out
bash harness/erpnext/cell.sh v15 x86-64 programs out-erpnext
```

## Licence

The harness is MIT-licensed (see `LICENSE`). Odoo, ERPNext and wkhtmltopdf belong to their makers and are used here as published.
