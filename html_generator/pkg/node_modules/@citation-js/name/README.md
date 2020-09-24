## Install

```js
npm install @citation-js/name
```

## Use

```js
let {parse, format} = require('@citation-js/name')

parse('First Last')
// { given: 'First', family: 'Last' }

format({ given: 'First', family: 'Last' })
// 'First Last'
```

### API

**`parse(String name) -> Object`**

* `String name`: Any name

**`format(Object name[, Boolean reversed]) -> String`**

* `Object name`: Any name
* `Boolean reversed`: Format as `Last, First` instead of `First Last`

---

Here, `Object` (CSL-JSON author format) has the following properties:

* `given`
* `family`
* `suffix`
* `dropping-particle`
* `non-dropping-particle`
