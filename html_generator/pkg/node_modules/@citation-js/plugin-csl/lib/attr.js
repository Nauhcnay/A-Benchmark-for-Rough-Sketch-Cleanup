"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.getPrefixedEntry = exports.getAttributedEntry = void 0;

const getAttributedEntry = (string, name, value) => string.replace(/^\s*<[a-z]+/i, `$& data-${name}="${value}"`);

exports.getAttributedEntry = getAttributedEntry;

const getPrefixedEntry = (value, id) => getAttributedEntry(value, 'csl-entry-id', id);

exports.getPrefixedEntry = getPrefixedEntry;