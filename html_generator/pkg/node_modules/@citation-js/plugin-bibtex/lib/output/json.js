"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;

var _type = _interopRequireDefault(require("./type"));

var _label = _interopRequireDefault(require("./label"));

var _name = require("@citation-js/name");

var _date = require("@citation-js/date");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function getNames(names) {
  return names.map(name => (0, _name.format)(name, true)).join(' and ');
}

const getBibTeXJSON = function (src, opts) {
  const res = {
    label: (0, _label.default)(src, opts),
    type: (0, _type.default)(src.type)
  };
  const props = {};
  const simple = {
    'collection-title': 'series',
    'container-title': ['chapter', 'inproceedings'].includes(src.type) ? 'booktitle' : 'journal',
    edition: 'edition',
    event: 'organization',
    DOI: 'doi',
    ISBN: 'isbn',
    ISSN: 'issn',
    issue: 'number',
    language: 'language',
    note: 'note',
    'number-of-pages': 'numpages',
    PMID: 'pmid',
    PMCID: 'pmcid',
    publisher: 'publisher',
    'publisher-place': 'address',
    title: 'title',
    URL: 'url',
    volume: 'volume'
  };

  for (let prop in simple) {
    if (src.hasOwnProperty(prop)) {
      props[simple[prop]] = src[prop] + '';
    }
  }

  if (src.author) {
    props.author = getNames(src.author);
  }

  if (src.editor) {
    props.editor = getNames(src.editor);
  }

  if (!src.note && src.accessed) {
    props.note = `[Online; accessed ${(0, _date.format)(src.accessed)}]`;
  }

  if (src.page) {
    props.pages = src.page.replace('-', '--');
  }

  if (src.issued && src.issued['date-parts']) {
    let dateParts = src.issued['date-parts'][0];

    if (dateParts.length > 0) {
      props.date = (0, _date.format)(src.issued);
      props.year = dateParts[0].toString();
    }

    if (dateParts.length > 1) {
      props.month = dateParts[1].toString();
    }

    if (dateParts.length > 2) {
      props.day = dateParts[2].toString();
    }
  }

  res.properties = props;
  return res;
};

var _default = getBibTeXJSON;
exports.default = _default;