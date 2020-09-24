"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;

var _core = require("@citation-js/core");

const bibtexTypes = {
  article: 'article',
  'article-journal': 'article',
  'article-magazine': 'article',
  'article-newspaper': 'article',
  book: 'book',
  chapter: 'incollection',
  graphic: 'misc',
  interview: 'misc',
  manuscript: 'unpublished',
  motion_picture: 'misc',
  'paper-conference': 'inproceedings',
  patent: 'patent',
  personal_communication: 'misc',
  report: 'techreport',
  thesis: 'phdthesis',
  webpage: 'misc'
};

const fetchBibTeXType = function (pubType) {
  if (pubType in bibtexTypes) {
    return bibtexTypes[pubType];
  } else {
    _core.logger.unmapped('[plugin-bibtex]', 'publication type', pubType);

    return 'misc';
  }
};

var _default = fetchBibTeXType;
exports.default = _default;