"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.getWrappedEntry = void 0;

const getAffix = (source, affix) => typeof affix === 'function' ? affix(source) : typeof affix === 'string' ? affix : '';

const htmlRegex = /^([^>]+>)([\s\S]+)(<[^<]+)$/i;

const getWrappedEntry = (value, source, {
  prepend,
  append
}) => {
  const [, start = '', content = value, end = ''] = value.match(htmlRegex) || [];
  const prefix = getAffix(source, prepend);
  const suffix = getAffix(source, append);
  return start + prefix + content + suffix + end;
};

exports.getWrappedEntry = getWrappedEntry;