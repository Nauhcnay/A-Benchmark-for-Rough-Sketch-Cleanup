"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.default = exports.getBibtxt = void 0;

var _json = _interopRequireDefault(require("./json"));

var _core = require("@citation-js/core");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const getBibtxt = function (src, dict, opts) {
  const entries = src.map(entry => {
    const bib = (0, _json.default)(entry, opts);
    bib.properties.type = bib.type;
    const properties = Object.keys(bib.properties).map(prop => dict.listItem.join(`${prop}: ${bib.properties[prop]}`)).join('');
    return dict.entry.join(`[${bib.label}]${dict.list.join(properties)}`);
  }).join('\n');
  return dict.bibliographyContainer.join(entries);
};

exports.getBibtxt = getBibtxt;

const getBibtxtWrapper = function (src, html) {
  const dict = _core.plugins.dict.get(html ? 'html' : 'text');

  return getBibtxt(src, dict);
};

var _default = getBibtxtWrapper;
exports.default = _default;