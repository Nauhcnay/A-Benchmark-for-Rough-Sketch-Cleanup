## Install

```js
npm install @citation-js/date
```

## Use

```js
let {parse, format} = require('@citation-js/date')

parse('2000-12-31')
// { 'date-parts': [[2000, 12, 31]] }

format({ 'date-parts': [[2000, 12, 31]] }, '/')
// '2000/12/31'
```

### Input

Supported formats:

  * Epoch time (in number form)
  * `YYYY-MM-DD`
  * `[+-]YYYYYY[Y...]-MM-DD`
  * `[DDD, ]DD MMM YYYY`
  * `M[M]/D[D]/YY[YY]` (1)
  * `D[D] M[M] Y[Y...]` (2, 1)
  * `[-]Y[Y...] M[M] D[D]` (2)
  * `D[D] MMM Y[Y...]` (2)
  * `[-]Y[Y...] MMM D[D]` (2)
  * `M[M] [-]Y[Y...]` (3, 5)
  * `[-]Y[Y...] M[M]` (3, 4, 5)
  * `MMM [-]Y[Y...]` (3, 5)
  * `[-]Y[Y...] MMM` (3, 5)
  * `[-]Y[Y...]` (5)

Generally, formats support trailing parts, which are disregarded.

  1. When the former of these formats overlaps with the latter, the
    former is preferred
  2. " ", ".", "-" and "/" are all supported as separator
  3. Any sequence of non-alphanumerical characters are supported as
    separator
  4. This format is only assumed if the year is bigger than the month
  5. This format doesn't support trailing parts

### API

**`parse(String date) -> Object`**

* `String date`: Any date

**`format(Object date[, String delimiter = '-']) -> String`**

* `Object date`: Any date
* `String delimiter`: Separate parts by delimiter

---

Here, `Object date` (CSL-JSON date format) can have the following properties:

* `date-parts`: array with one or two dates, each date being an array of [year, month, day], the last two parts being optional
* `raw`: raw date
