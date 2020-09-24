"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = void 0;
const stopWords = ['the', 'a', 'an'];

const safeSlug = text => {
  return !text ? '' : text.replace(/<\/?.*?>/g, '').split(/[\u0020-\u002F\u003A-\u0040\u005B-\u005E\u0060\u007B-\u007F]+/).find(word => word.length && !stopWords.includes(word.toLowerCase()));
};

const getBibTeXLabel = function (entry = {}, opts = {}) {
  const {
    generateLabel = true
  } = opts;

  if (entry['citation-label']) {
    return entry['citation-label'];
  } else if (!generateLabel) {
    return entry.id;
  }

  let res = '';

  if (entry.author) {
    res += safeSlug(entry.author[0].family || entry.author[0].literal);
  }

  if (entry.issued && entry.issued['date-parts'] && entry.issued['date-parts'][0]) {
    res += entry.issued['date-parts'][0][0];
  }

  if (entry['year-suffix']) {
    res += entry['year-suffix'];
  } else if (entry.title) {
    res += safeSlug(entry.title);
  }

  return res || entry.id;
};

var _default = getBibTeXLabel;
exports.default = _default;