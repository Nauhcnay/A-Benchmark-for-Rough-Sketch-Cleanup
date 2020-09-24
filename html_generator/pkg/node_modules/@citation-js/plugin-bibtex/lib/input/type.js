"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = exports.parse = void 0;

var _core = require("@citation-js/core");

const typeMap = {
  article: 'article-journal',
  book: 'book',
  booklet: 'book',
  proceedings: 'book',
  manual: false,
  mastersthesis: 'thesis',
  misc: false,
  inbook: 'chapter',
  incollection: 'chapter',
  conference: 'paper-conference',
  inproceedings: 'paper-conference',
  online: 'website',
  patent: 'patent',
  phdthesis: 'thesis',
  techreport: 'report',
  unpublished: 'manuscript'
};

const parseBibTeXType = function (pubType) {
  if (!typeMap.hasOwnProperty(pubType)) {
    _core.logger.unmapped('[plugin-bibtex]', 'publication type', pubType);

    return 'book';
  } else if (typeMap[pubType] === false) {
    return 'book';
  } else {
    return typeMap[pubType];
  }
};

exports.default = exports.parse = parseBibTeXType;